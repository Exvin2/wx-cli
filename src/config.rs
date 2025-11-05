use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::env;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    pub openrouter_api_key: Option<String>,
    pub openrouter_model: String,
    pub gemini_api_key: Option<String>,
    pub gemini_model: String,
    pub temperature: f32,
    pub max_tokens: u32,
    pub units: Units,
    pub offline: bool,
    pub debug: bool,
    pub privacy_mode: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Units {
    Imperial,
    Metric,
}

impl Config {
    pub fn load(offline: bool, debug: bool) -> Result<Self> {
        // Load .env file if present
        dotenv::dotenv().ok();

        let config = Config {
            openrouter_api_key: env::var("OPENROUTER_API_KEY").ok(),
            openrouter_model: env::var("OPENROUTER_MODEL")
                .unwrap_or_else(|_| "openrouter/auto".to_string()),
            gemini_api_key: env::var("GEMINI_API_KEY")
                .or_else(|_| env::var("GOOGLE_API_KEY"))
                .ok(),
            gemini_model: env::var("GEMINI_MODEL")
                .unwrap_or_else(|_| "gemini-2.0-flash-exp".to_string()),
            temperature: env::var("AI_TEMPERATURE")
                .ok()
                .and_then(|s| s.parse().ok())
                .unwrap_or(0.2),
            max_tokens: env::var("AI_MAX_TOKENS")
                .ok()
                .and_then(|s| s.parse().ok())
                .unwrap_or(900),
            units: match env::var("UNITS")
                .unwrap_or_else(|_| "imperial".to_string())
                .to_lowercase()
                .as_str()
            {
                "metric" => Units::Metric,
                _ => Units::Imperial,
            },
            offline: offline || env::var("WX_OFFLINE").ok() == Some("1".to_string()),
            debug,
            privacy_mode: env::var("PRIVACY_MODE")
                .ok()
                .map(|v| v != "0")
                .unwrap_or(true),
        };

        Ok(config)
    }
}
