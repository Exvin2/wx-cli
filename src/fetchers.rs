use anyhow::Result;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FeaturePack {
    pub location: Option<Location>,
    pub current_conditions: Option<serde_json::Value>,
    pub forecast: Option<serde_json::Value>,
    pub alerts: Vec<Alert>,
    pub timestamp: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Location {
    pub name: String,
    pub lat: f64,
    pub lon: f64,
    pub timezone: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Alert {
    pub event: String,
    pub severity: String,
    pub description: String,
    pub areas: Vec<String>,
}

impl FeaturePack {
    /// Create synthetic feature pack for offline mode
    pub fn synthetic(location_query: &str) -> Self {
        FeaturePack {
            location: Some(Location {
                name: location_query.to_string(),
                lat: 47.6,
                lon: -122.3,
                timezone: Some("America/Los_Angeles".to_string()),
            }),
            current_conditions: Some(serde_json::json!({
                "temp": 50,
                "wind": 10,
                "humidity": 65,
                "conditions": "Clear"
            })),
            forecast: Some(serde_json::json!({
                "periods": []
            })),
            alerts: vec![],
            timestamp: chrono::Utc::now().to_rfc3339(),
        }
    }

    /// Fetch real weather data (async)
    pub async fn fetch(location_query: &str, offline: bool) -> Result<Self> {
        if offline {
            return Ok(Self::synthetic(location_query));
        }

        // TODO: Implement real fetching
        // - Geocode location
        // - Fetch from Open-Meteo
        // - Fetch from NWS
        // - Fetch alerts

        Ok(Self::synthetic(location_query))
    }

    /// Blocking version of fetch
    pub fn fetch_blocking(location_query: &str, offline: bool) -> Result<Self> {
        let rt = tokio::runtime::Runtime::new()?;
        rt.block_on(Self::fetch(location_query, offline))
    }
}
