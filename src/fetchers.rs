use anyhow::{Result, anyhow};
use serde::{Deserialize, Serialize};
use std::time::Duration;

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

        // Step 1: Geocode location
        let location = geocode_location(location_query).await?;

        // Step 2: Fetch NWS forecast data
        let forecast_periods = fetch_nws_forecast(location.lat, location.lon).await?;

        // Step 3: Build current conditions from first period
        let current_conditions = if let Some(first) = forecast_periods.first() {
            serde_json::json!({
                "temp": first.temperature,
                "temp_unit": &first.temperature_unit,
                "wind": &first.wind_speed,
                "wind_direction": &first.wind_direction,
                "conditions": &first.short_forecast
            })
        } else {
            serde_json::json!({})
        };

        // Step 4: Package forecast data
        let forecast = serde_json::json!({
            "periods": forecast_periods
        });

        Ok(FeaturePack {
            location: Some(location),
            current_conditions: Some(current_conditions),
            forecast: Some(forecast),
            alerts: vec![], // TODO: Fetch alerts from NWS
            timestamp: chrono::Utc::now().to_rfc3339(),
        })
    }

    /// Blocking version of fetch
    pub fn fetch_blocking(location_query: &str, offline: bool) -> Result<Self> {
        let rt = tokio::runtime::Runtime::new()?;
        rt.block_on(Self::fetch(location_query, offline))
    }
}

/// Geocoding response from Nominatim
#[derive(Debug, Deserialize)]
struct GeocodingResult {
    lat: String,
    lon: String,
    display_name: String,
}

/// Geocode a location query to coordinates using Nominatim
async fn geocode_location(query: &str) -> Result<Location> {
    let url = format!(
        "https://nominatim.openstreetmap.org/search?q={}&format=json&limit=1",
        urlencoding::encode(query)
    );

    let client = reqwest::Client::builder()
        .user_agent("wx-cli/0.2.0")
        .timeout(Duration::from_secs(10))
        .build()?;

    let results: Vec<GeocodingResult> = client
        .get(&url)
        .send()
        .await?
        .json()
        .await?;

    if let Some(result) = results.first() {
        Ok(Location {
            name: result.display_name.clone(),
            lat: result.lat.parse()?,
            lon: result.lon.parse()?,
            timezone: None, // Will be populated by NWS if needed
        })
    } else {
        Err(anyhow!("Location '{}' not found", query))
    }
}

/// NWS Points API response (subset)
#[derive(Debug, Deserialize)]
struct NWSPointsResponse {
    properties: NWSPointsProperties,
}

#[derive(Debug, Deserialize)]
struct NWSPointsProperties {
    #[serde(rename = "forecastHourly")]
    forecast_hourly: String,
    #[serde(rename = "relativeLocation")]
    relative_location: NWSRelativeLocation,
}

#[derive(Debug, Deserialize)]
struct NWSRelativeLocation {
    properties: NWSRelativeLocationProperties,
}

#[derive(Debug, Deserialize)]
struct NWSRelativeLocationProperties {
    city: String,
    state: String,
}

/// NWS Forecast API response (subset)
#[derive(Debug, Deserialize)]
struct NWSForecastResponse {
    properties: NWSForecastProperties,
}

#[derive(Debug, Deserialize)]
struct NWSForecastProperties {
    periods: Vec<NWSForecastPeriod>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NWSForecastPeriod {
    pub name: String,
    pub temperature: i32,
    #[serde(rename = "temperatureUnit")]
    pub temperature_unit: String,
    #[serde(rename = "windSpeed")]
    pub wind_speed: String,
    #[serde(rename = "windDirection")]
    pub wind_direction: String,
    #[serde(rename = "shortForecast")]
    pub short_forecast: String,
    #[serde(rename = "detailedForecast")]
    pub detailed_forecast: String,
}

/// Fetch NWS forecast data
async fn fetch_nws_forecast(lat: f64, lon: f64) -> Result<Vec<NWSForecastPeriod>> {
    let client = reqwest::Client::builder()
        .user_agent("wx-cli/0.2.0 (weather storytelling CLI)")
        .timeout(Duration::from_secs(15))
        .build()?;

    // Step 1: Get forecast URL from points API
    let points_url = format!("https://api.weather.gov/points/{:.4},{:.4}", lat, lon);
    let points_response: NWSPointsResponse = client
        .get(&points_url)
        .send()
        .await?
        .json()
        .await?;

    // Step 2: Fetch hourly forecast
    let forecast_response: NWSForecastResponse = client
        .get(&points_response.properties.forecast_hourly)
        .send()
        .await?
        .json()
        .await?;

    Ok(forecast_response.properties.periods)
}
