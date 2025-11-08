use anyhow::Result;
use serde::{Deserialize, Serialize};

/// A complete weather story with narrative sections
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WeatherStory {
    pub setup: String,
    pub current: String,
    pub evolution: Timeline,
    pub meteorology: String,
    pub decisions: Vec<Decision>,
    pub confidence: ConfidenceNote,
    pub bottom_line: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub meta: Option<serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Timeline {
    pub phases: Vec<TimelinePhase>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TimelinePhase {
    pub start_time: String,
    pub end_time: String,
    pub description: String,
    pub key_changes: Vec<String>,
    pub confidence: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Decision {
    pub activity: String,
    pub recommendation: String,
    pub reasoning: String,
    pub timing: Option<String>,
    pub confidence: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConfidenceNote {
    pub primary_uncertainty: String,
    pub alternative_scenarios: Vec<String>,
    pub confidence_level: ConfidenceLevel,
    pub rationale: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ConfidenceLevel {
    High,
    Medium,
    Low,
}

impl WeatherStory {
    /// Create a synthetic story for offline mode
    pub fn synthetic(location: &str) -> Self {
        WeatherStory {
            setup: format!(
                "High pressure dominates over {}, creating stable atmospheric conditions.",
                location
            ),
            current: "Clear skies with light winds. Temperature comfortable for the season."
                .to_string(),
            evolution: Timeline {
                phases: vec![
                    TimelinePhase {
                        start_time: "Now".to_string(),
                        end_time: "6 hours".to_string(),
                        description: "Conditions remain stable with gradual temperature change"
                            .to_string(),
                        key_changes: vec!["Slow temperature transition".to_string()],
                        confidence: 0.8,
                    },
                    TimelinePhase {
                        start_time: "6 hours".to_string(),
                        end_time: "12 hours".to_string(),
                        description: "Continuing stable pattern".to_string(),
                        key_changes: vec![],
                        confidence: 0.7,
                    },
                ],
            },
            meteorology: "High pressure ridge maintains control, suppressing cloud development and precipitation. Classic fair weather pattern.".to_string(),
            decisions: vec![
                Decision {
                    activity: "Outdoor activities".to_string(),
                    recommendation: "Excellent conditions for any outdoor plans".to_string(),
                    reasoning: "Stable weather with no precipitation expected".to_string(),
                    timing: Some("Any time today".to_string()),
                    confidence: 0.85,
                },
            ],
            confidence: ConfidenceNote {
                primary_uncertainty: "Timing of next weather system".to_string(),
                alternative_scenarios: vec![
                    "Pattern holds longer than expected".to_string(),
                ],
                confidence_level: ConfidenceLevel::Medium,
                rationale: "Synthetic data - offline mode".to_string(),
            },
            bottom_line: format!("Stable, fair weather continues over {} with no significant changes expected.", location),
            meta: None,
        }
    }

    /// Generate story using AI from weather data
    pub fn generate_with_ai(
        feature_pack: &crate::fetchers::FeaturePack,
        config: &crate::config::Config,
    ) -> Result<Self> {
        // Use blocking runtime for sync context
        let rt = tokio::runtime::Runtime::new()?;
        rt.block_on(Self::generate_with_ai_async(feature_pack, config))
    }

    /// Async version of AI generation
    async fn generate_with_ai_async(
        feature_pack: &crate::fetchers::FeaturePack,
        config: &crate::config::Config,
    ) -> Result<Self> {
        // Prefer Gemini (free tier available), fall back to OpenRouter
        if let Some(gemini_key) = &config.gemini_api_key {
            Self::generate_with_gemini(feature_pack, config, gemini_key).await
        } else if let Some(openrouter_key) = &config.openrouter_api_key {
            Self::generate_with_openrouter(feature_pack, config, openrouter_key).await
        } else {
            // No API key available, use synthetic
            let location_name = feature_pack
                .location
                .as_ref()
                .map(|l| l.name.as_str())
                .unwrap_or("Unknown");
            Ok(Self::synthetic(location_name))
        }
    }

    /// Generate story using Google Gemini API
    async fn generate_with_gemini(
        feature_pack: &crate::fetchers::FeaturePack,
        config: &crate::config::Config,
        api_key: &str,
    ) -> Result<Self> {
        use reqwest::Client;
        use serde_json::json;

        let prompt = Self::build_story_prompt(feature_pack)?;

        let url = format!(
            "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent?key={}",
            config.gemini_model, api_key
        );

        let client = Client::new();
        let response = client
            .post(&url)
            .json(&json!({
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": config.temperature,
                    "maxOutputTokens": config.max_tokens,
                    "responseMimeType": "application/json"
                }
            }))
            .send()
            .await?;

        let response_json: serde_json::Value = response.json().await?;

        // Extract text from Gemini response
        let story_text = response_json["candidates"][0]["content"]["parts"][0]["text"]
            .as_str()
            .ok_or_else(|| anyhow::anyhow!("Failed to extract story from Gemini response"))?;

        // Parse JSON story
        let story: WeatherStory = serde_json::from_str(story_text)?;
        Ok(story)
    }

    /// Generate story using OpenRouter API
    async fn generate_with_openrouter(
        feature_pack: &crate::fetchers::FeaturePack,
        config: &crate::config::Config,
        api_key: &str,
    ) -> Result<Self> {
        use reqwest::Client;
        use serde_json::json;

        let prompt = Self::build_story_prompt(feature_pack)?;

        let client = Client::new();
        let response = client
            .post("https://openrouter.ai/api/v1/chat/completions")
            .header("Authorization", format!("Bearer {}", api_key))
            .header("Content-Type", "application/json")
            .json(&json!({
                "model": config.openrouter_model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
                "response_format": {"type": "json_object"}
            }))
            .send()
            .await?;

        let response_json: serde_json::Value = response.json().await?;

        // Extract text from OpenRouter response
        let story_text = response_json["choices"][0]["message"]["content"]
            .as_str()
            .ok_or_else(|| anyhow::anyhow!("Failed to extract story from OpenRouter response"))?;

        // Parse JSON story
        let story: WeatherStory = serde_json::from_str(story_text)?;
        Ok(story)
    }

    /// Build the AI prompt from feature pack data
    fn build_story_prompt(feature_pack: &crate::fetchers::FeaturePack) -> Result<String> {
        let location_name = feature_pack
            .location
            .as_ref()
            .map(|l| l.name.clone())
            .unwrap_or_else(|| "Unknown Location".to_string());

        let forecast_summary = if let Some(forecast) = &feature_pack.forecast {
            serde_json::to_string_pretty(forecast)?
        } else {
            "No forecast data available".to_string()
        };

        let current_summary = if let Some(current) = &feature_pack.current_conditions {
            serde_json::to_string_pretty(current)?
        } else {
            "No current conditions available".to_string()
        };

        // Include alerts if present
        let alerts_section = if !feature_pack.alerts.is_empty() {
            let alerts_json = serde_json::to_string_pretty(&feature_pack.alerts)?;
            format!("\n\n🚨 ACTIVE ALERTS:\n{}\n\nIMPORTANT: Integrate these alerts into your story. Prioritize safety. Explain what these alerts mean for decisions.", alerts_json)
        } else {
            String::new()
        };

        Ok(format!(
            r#"You are an expert meteorologist crafting a weather story for {}.

Weather Data:
Current Conditions: {}
Forecast: {}{}

Create a compelling, scientifically-grounded weather narrative as JSON:

{{
  "setup": "Large-scale meteorological pattern (2-3 sentences). Mention pressure systems, fronts, jet stream position, moisture sources. Use technical terms like 'low-pressure trough', 'high-pressure ridge', 'atmospheric river', 'convergence zone'.",

  "current": "Vivid description of current conditions (2 sentences). Include sensory details and immediate impacts.",

  "evolution": {{
    "phases": [
      {{
        "start_time": "Now",
        "end_time": "3 hours",
        "description": "Detailed phase description with mechanisms (lifting, cooling, mixing)",
        "key_changes": ["Specific measurable change", "Another specific change"],
        "confidence": 0.85
      }}
      // Include 3-5 phases covering next 12-24 hours
    ]
  }},

  "meteorology": "Deep dive into WHY (3-4 sentences). Explain atmospheric physics: Why is this system behaving this way? What forcings are at play? Mention CAPE, lifted index, lapse rates, wind shear, dewpoint spread, or other relevant parameters when applicable. Make the reader understand the cause-effect chain.",

  "decisions": [
    {{
      "activity": "Specific activity (e.g., 'Morning commute', 'Outdoor lunch', 'Evening flight')",
      "recommendation": "CLEAR actionable advice with specific timing",
      "reasoning": "Physical reason based on meteorology (not just 'because rain')",
      "timing": "Exact time window (e.g., 'Leave before 7 AM or after 9 PM')",
      "confidence": 0.8
    }}
    // Include 3-5 decision items covering different activities and time windows
  ],

  "confidence": {{
    "primary_uncertainty": "Specific meteorological uncertainty (e.g., 'Exact timing of cold front passage', 'Convective initiation location')",
    "alternative_scenarios": [
      "If X happens: outcome",
      "If Y happens: different outcome"
    ],
    "confidence_level": "High|Medium|Low",
    "rationale": "Why we have this confidence (model agreement, pattern recognition, physical reasoning)"
  }},

  "bottom_line": "One punchy sentence combining impact + timing + action. Make it memorable."
}}

CRITICAL Guidelines:
- EXPLAIN MECHANISMS, not just patterns. Say WHY air rises, WHY clouds form, WHY winds shift
- Use meteorological terminology appropriately: CAPE, vorticity, baroclinic zones, thermal advection, etc.
- Decisions must be TIME-SPECIFIC and ACTIONABLE (not vague like "be careful")
- If alerts are present, EMPHASIZE THEM and explain their implications
- Confidence should reflect actual meteorological uncertainty (not just hedging)
- Timeline phases should show EVOLUTION not just snapshots
- Bottom line should tell someone "what to do when" in one sentence

Return ONLY the JSON object, no other text."#,
            location_name, current_summary, forecast_summary, alerts_section
        ))
    }
}

impl Timeline {
    pub fn to_visualization(&self) -> String {
        let mut lines = Vec::new();
        let phase_count = self.phases.len();

        for (i, phase) in self.phases.iter().enumerate() {
            let prefix = if i < phase_count - 1 { "├─" } else { "└─" };
            let time_range = format!("{} – {}", phase.start_time, phase.end_time);

            lines.push(format!("{} {}: {}", prefix, time_range, phase.description));

            // Add key changes
            for change in &phase.key_changes {
                let indent = if i < phase_count - 1 { "│  " } else { "   " };
                lines.push(format!("{}  • {}", indent, change));
            }

            // Add confidence bar
            let conf_bar = confidence_bar(phase.confidence);
            let indent = if i < phase_count - 1 { "│  " } else { "   " };
            lines.push(format!("{}Confidence: {}", indent, conf_bar));

            // Blank line between phases
            if i < phase_count - 1 {
                lines.push("│".to_string());
            }
        }

        lines.join("\n")
    }
}

/// Create visual confidence indicator
pub fn confidence_bar(confidence: f32) -> String {
    let filled = (confidence * 10.0) as usize;
    let empty = 10 - filled;
    "█".repeat(filled) + &"░".repeat(empty)
}

/// Map activity to emoji
pub fn activity_emoji(activity: &str) -> &'static str {
    let activity_lower = activity.to_lowercase();

    if activity_lower.contains("commute") {
        "🚗"
    } else if activity_lower.contains("bike") {
        "🚴"
    } else if activity_lower.contains("run") {
        "🏃"
    } else if activity_lower.contains("walk") {
        "🚶"
    } else if activity_lower.contains("outdoor") {
        "🌳"
    } else if activity_lower.contains("lunch") {
        "☕"
    } else if activity_lower.contains("dinner") {
        "🍽️"
    } else if activity_lower.contains("aviation") {
        "✈️"
    } else if activity_lower.contains("sailing") || activity_lower.contains("marine") {
        "⛵"
    } else if activity_lower.contains("sports") {
        "⚽"
    } else if activity_lower.contains("event") {
        "📅"
    } else if activity_lower.contains("travel") {
        "🧳"
    } else if activity_lower.contains("work") {
        "💼"
    } else if activity_lower.contains("school") {
        "🎒"
    } else {
        "📌"
    }
}
