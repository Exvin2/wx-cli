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

    /// Generate story using AI (calls Python subprocess as bridge)
    pub fn generate_with_ai(
        location: &str,
        _feature_pack: &serde_json::Value,
        _config: &crate::config::Config,
    ) -> Result<Self> {
        // TODO: Bridge to Python for AI generation
        // For now, return synthetic
        Ok(Self::synthetic(location))
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
