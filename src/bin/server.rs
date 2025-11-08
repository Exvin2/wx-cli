use axum::{
    extract::{Query, State},
    http::{StatusCode, header},
    response::{IntoResponse, Response},
    routing::{get, post},
    Json, Router,
};
use serde::{Deserialize, Serialize};
use std::net::SocketAddr;
use std::sync::Arc;
use tower_http::cors::{CorsLayer, Any};
use tower_http::services::ServeDir;
use tower_http::trace::TraceLayer;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

// Import wx library modules
use wx::{config, fetchers, story};

#[derive(Clone)]
struct AppState {
    config: config::Config,
}

#[tokio::main]
async fn main() {
    // Initialize tracing
    tracing_subscriber::registry()
        .with(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "wx_server=debug,tower_http=debug".into()),
        )
        .with(tracing_subscriber::fmt::layer())
        .init();

    // Load config
    let config = config::Config::load(false, true).expect("Failed to load config");
    let state = Arc::new(AppState { config });

    // Build router
    let app = Router::new()
        .route("/api/health", get(health))
        .route("/api/story", get(get_story))
        .route("/api/forecast", get(get_forecast))
        .route("/api/alerts", get(get_alerts))
        .layer(
            CorsLayer::new()
                .allow_origin(Any)
                .allow_methods(Any)
                .allow_headers(Any),
        )
        .layer(TraceLayer::new_for_http())
        .with_state(state)
        // Serve static files from web directory (index.html, app.js)
        .fallback_service(ServeDir::new("web"));

    // Start server
    let addr = SocketAddr::from(([0, 0, 0, 0], 3000));
    tracing::info!("🚀 wx-server listening on {}", addr);
    tracing::info!("🌐 Web UI: http://localhost:3000");
    tracing::info!("📖 API endpoints:");
    tracing::info!("   GET  /api/health");
    tracing::info!("   GET  /api/story?location=Seattle");
    tracing::info!("   GET  /api/forecast?location=Seattle");
    tracing::info!("   GET  /api/alerts?location=Seattle");

    let listener = tokio::net::TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}

async fn health() -> impl IntoResponse {
    Json(serde_json::json!({
        "status": "ok",
        "version": "0.2.0"
    }))
}

#[derive(Deserialize)]
struct LocationQuery {
    location: String,
    #[serde(default)]
    verbose: bool,
}

async fn get_story(
    State(state): State<Arc<AppState>>,
    Query(params): Query<LocationQuery>,
) -> Result<Json<story::WeatherStory>, AppError> {
    // Fetch weather data
    let feature_pack = fetchers::FeaturePack::fetch(&params.location, state.config.offline).await
        .map_err(|e| AppError::Internal(e.to_string()))?;

    // Generate story
    let story_result = if state.config.offline {
        let location_name = feature_pack
            .location
            .as_ref()
            .map(|l| l.name.as_str())
            .unwrap_or(&params.location);
        story::WeatherStory::synthetic(location_name)
    } else {
        story::WeatherStory::generate_with_ai(&feature_pack, &state.config)
            .unwrap_or_else(|_| {
                let location_name = feature_pack
                    .location
                    .as_ref()
                    .map(|l| l.name.as_str())
                    .unwrap_or(&params.location);
                story::WeatherStory::synthetic(location_name)
            })
    };

    Ok(Json(story_result))
}

async fn get_forecast(
    State(state): State<Arc<AppState>>,
    Query(params): Query<LocationQuery>,
) -> Result<Json<fetchers::FeaturePack>, AppError> {
    let feature_pack = fetchers::FeaturePack::fetch(&params.location, state.config.offline).await
        .map_err(|e| AppError::Internal(e.to_string()))?;

    Ok(Json(feature_pack))
}

#[derive(Serialize)]
struct AlertsResponse {
    alerts: Vec<fetchers::Alert>,
    count: usize,
}

async fn get_alerts(
    State(state): State<Arc<AppState>>,
    Query(params): Query<LocationQuery>,
) -> Result<Json<AlertsResponse>, AppError> {
    let feature_pack = fetchers::FeaturePack::fetch(&params.location, state.config.offline).await
        .map_err(|e| AppError::Internal(e.to_string()))?;

    let count = feature_pack.alerts.len();
    Ok(Json(AlertsResponse {
        alerts: feature_pack.alerts,
        count,
    }))
}

// Error handling
enum AppError {
    Internal(String),
}

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        let (status, error_message) = match self {
            AppError::Internal(msg) => (StatusCode::INTERNAL_SERVER_ERROR, msg),
        };

        let body = Json(serde_json::json!({
            "error": error_message
        }));

        (status, body).into_response()
    }
}
