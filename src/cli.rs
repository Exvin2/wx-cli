use anyhow::Result;
use crate::config::Config;
use crate::fetchers::FeaturePack;
use crate::story::WeatherStory;
use crate::render::{render_story, render_story_json};

pub fn handle_story(
    config: &Config,
    place: &str,
    _when: Option<&str>,
    _horizon: &str,
    _focus: Option<&str>,
    verbose: bool,
    json: bool,
) -> Result<()> {
    // Fetch weather data
    let feature_pack = FeaturePack::fetch_blocking(place, config.offline)?;

    // Generate story
    let story = if config.offline {
        WeatherStory::synthetic(place)
    } else {
        // Try AI generation, fallback to synthetic
        WeatherStory::generate_with_ai(
            place,
            &serde_json::to_value(&feature_pack)?,
            config,
        )
        .unwrap_or_else(|_| WeatherStory::synthetic(place))
    };

    // Render
    if json {
        println!("{}", render_story_json(&story));
    } else {
        render_story(&story, verbose);
    }

    Ok(())
}

pub fn handle_forecast(
    config: &Config,
    place: &str,
    _when: Option<&str>,
    _horizon: &str,
    _focus: Option<&str>,
    _verbose: bool,
    json: bool,
) -> Result<()> {
    let feature_pack = FeaturePack::fetch_blocking(place, config.offline)?;

    if json {
        println!("{}", serde_json::to_string_pretty(&feature_pack)?);
    } else {
        println!("Forecast for {} (coming soon - use `wx story` for now)", place);
    }

    Ok(())
}

pub fn handle_risk(
    config: &Config,
    place: &str,
    _hazards: Option<&str>,
    _verbose: bool,
    json: bool,
) -> Result<()> {
    let feature_pack = FeaturePack::fetch_blocking(place, config.offline)?;

    if json {
        println!("{}", serde_json::to_string_pretty(&feature_pack)?);
    } else {
        println!("Risk assessment for {} (coming soon - use `wx story` for now)", place);
    }

    Ok(())
}

pub fn handle_alerts(
    config: &Config,
    place: &str,
    _ai: bool,
    _verbose: bool,
    json: bool,
) -> Result<()> {
    let feature_pack = FeaturePack::fetch_blocking(place, config.offline)?;

    if json {
        println!("{}", serde_json::to_string_pretty(&feature_pack.alerts)?);
    } else {
        if feature_pack.alerts.is_empty() {
            println!("No active alerts for {}", place);
        } else {
            println!("Active alerts for {}:", place);
            for alert in &feature_pack.alerts {
                println!("  • {} - {}", alert.event, alert.severity);
            }
        }
    }

    Ok(())
}

pub fn handle_chat(_config: &Config, _verbose: bool) -> Result<()> {
    println!("Interactive chat mode (coming soon)");
    println!("For now, use `wx story <location>` for narrative weather stories");
    Ok(())
}

pub fn handle_world(_config: &Config, _severe: bool, _verbose: bool, json: bool) -> Result<()> {
    if json {
        println!("{{}}");
    } else {
        println!("World weather snapshot (coming soon)");
        println!("For now, use `wx story <location>` for specific locations");
    }
    Ok(())
}

pub fn handle_question(_config: &Config, question: &str, _verbose: bool, json: bool) -> Result<()> {
    if json {
        println!("{{\"question\": \"{}\" }}", question);
    } else {
        println!("Question: {}", question);
        println!("(Freeform questions coming soon - try `wx story <location>` for narratives)");
    }
    Ok(())
}
