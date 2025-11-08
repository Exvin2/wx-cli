use crate::story::{WeatherStory, ConfidenceLevel, confidence_bar, activity_emoji};
use crate::fetchers::Alert;
use colored::*;

/// Render a weather story to the terminal
pub fn render_story(story: &WeatherStory, alerts: &[Alert], verbose: bool) {
    // CRITICAL: Show alerts FIRST if present
    if !alerts.is_empty() {
        render_alerts(alerts);
    }

    // Title
    println!("\n{}", "📖  Weather Story".cyan().bold());
    println!();

    // THE SETUP
    print_section_header("🌤️  THE SETUP", "What's Happening", "blue");
    println!("{}", story.setup);
    println!();

    // THE PRESENT
    print_section_header("🌡️  THE PRESENT", "", "cyan");
    println!("{}", story.current);
    println!();

    // THE EVOLUTION
    if !story.evolution.phases.is_empty() {
        print_section_header("⏳  THE EVOLUTION", "Your Next Hours", "yellow");
        println!("{}", story.evolution.to_visualization());
        println!();
    }

    // THE METEOROLOGY
    print_section_header("🌀  THE METEOROLOGY", "Why This Matters", "magenta");
    println!("{}", story.meteorology);
    println!();

    // YOUR DECISIONS
    if !story.decisions.is_empty() {
        print_section_header("🎯  YOUR DECISIONS", "What To Do", "green");
        for decision in &story.decisions {
            let emoji = activity_emoji(&decision.activity);
            println!("{} {}", emoji, decision.activity.bold());
            println!("   → {}", decision.recommendation);
            println!("   {}", format!("Why: {}", decision.reasoning).dimmed());

            if let Some(timing) = &decision.timing {
                println!("   {}", format!("Best timing: {}", timing).dimmed());
            }

            let conf_bar = confidence_bar(decision.confidence);
            println!("   {}", format!("Confidence: {}", conf_bar).dimmed());
            println!();
        }
    }

    // CONFIDENCE NOTES
    print_section_header("📊  CONFIDENCE NOTES", "", "white");
    println!(
        "{} {}",
        "⚠️  Primary uncertainty:".yellow(),
        story.confidence.primary_uncertainty
    );

    if !story.confidence.alternative_scenarios.is_empty() {
        println!();
        println!("{}", "Alternative scenarios:".cyan());
        for scenario in &story.confidence.alternative_scenarios {
            println!("  • {}", scenario);
        }
    }

    println!();
    let level_str = match story.confidence.confidence_level {
        ConfidenceLevel::High => "High".green(),
        ConfidenceLevel::Medium => "Medium".yellow(),
        ConfidenceLevel::Low => "Low".red(),
    };
    println!("Overall confidence: {}", level_str);

    if !story.confidence.rationale.is_empty() {
        println!("{}", story.confidence.rationale.dimmed());
    }
    println!();

    // BOTTOM LINE
    println!("{} {}", "💡".yellow(), story.bottom_line.bold().yellow());
    println!();

    // Verbose metadata
    if verbose {
        if let Some(meta) = &story.meta {
            println!("{}", format!("Meta: {}", meta).dimmed());
        }
    }
}

fn print_section_header(title: &str, subtitle: &str, color: &str) {
    let separator = "━".repeat(60);

    println!("{}", separator.color(color));
    if subtitle.is_empty() {
        println!("{}", title.bold());
    } else {
        println!("{} {}", title.bold(), subtitle.dimmed());
    }
    println!("{}", separator.color(color));
}

/// Render active alerts with high visibility
fn render_alerts(alerts: &[Alert]) {
    println!();
    let alert_header = "🚨  ACTIVE WEATHER ALERTS  🚨";
    let separator = "═".repeat(alert_header.len());

    println!("{}", separator.red().bold());
    println!("{}", alert_header.red().bold().on_bright_black());
    println!("{}", separator.red().bold());
    println!();

    for (i, alert) in alerts.iter().enumerate() {
        // Severity color coding
        let severity_display = match alert.severity.to_uppercase().as_str() {
            "EXTREME" => format!("⚠️  {} ⚠️", alert.severity.to_uppercase()).red().bold().on_bright_white(),
            "SEVERE" => alert.severity.to_uppercase().red().bold(),
            "MODERATE" => alert.severity.to_uppercase().yellow().bold(),
            _ => alert.severity.to_uppercase().white().bold(),
        };

        println!("{} {}", format!("Alert {}/{}:", i + 1, alerts.len()).dimmed(), severity_display);
        println!("{}", alert.event.bright_red().bold());
        println!();
        println!("{}", alert.description);

        if !alert.areas.is_empty() {
            println!();
            println!("{}", "Affected areas:".dimmed());
            for area in &alert.areas {
                println!("  • {}", area);
            }
        }

        println!();
        println!("{}", "─".repeat(60).red());
        println!();
    }
}

/// Render story as JSON
pub fn render_story_json(story: &WeatherStory) -> String {
    serde_json::to_string_pretty(story).unwrap_or_else(|_| "{}".to_string())
}
