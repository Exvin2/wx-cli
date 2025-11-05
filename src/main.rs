use anyhow::Result;
use clap::{Parser, Subcommand};

mod cli;
mod config;
mod fetchers;
mod render;
mod story;

#[derive(Parser)]
#[command(name = "wx")]
#[command(about = "Lightning-fast weather CLI with AI storytelling", long_about = None)]
#[command(version)]
struct Cli {
    /// Enable debug output
    #[arg(short, long)]
    debug: bool,

    /// Output as JSON
    #[arg(long)]
    json: bool,

    /// Verbose output (allow longer responses)
    #[arg(short, long)]
    verbose: bool,

    /// Offline mode (use cached/synthetic data)
    #[arg(long)]
    offline: bool,

    /// Subcommand to execute
    #[command(subcommand)]
    command: Option<Commands>,

    /// Freeform question (when no subcommand given)
    question: Option<String>,
}

#[derive(Subcommand)]
enum Commands {
    /// Generate a weather story (narrative format)
    Story {
        /// Location (city name or lat,lon)
        place: String,

        /// Time reference (e.g., "tomorrow", "tonight")
        #[arg(long)]
        when: Option<String>,

        /// Time horizon (6h, 12h, 24h, 3d)
        #[arg(long, default_value = "12h")]
        horizon: String,

        /// Activity focus (e.g., "commuting", "aviation")
        #[arg(long)]
        focus: Option<String>,
    },

    /// Get forecast for a location
    Forecast {
        /// Location (city name or lat,lon)
        place: String,

        /// Time reference
        #[arg(long)]
        when: Option<String>,

        /// Forecast horizon
        #[arg(long, default_value = "24h")]
        horizon: String,

        /// Focus area
        #[arg(long)]
        focus: Option<String>,
    },

    /// Get risk assessment
    Risk {
        /// Location (city name or lat,lon)
        place: String,

        /// Comma-separated hazards
        #[arg(long)]
        hazards: Option<String>,
    },

    /// Get active alerts
    Alerts {
        /// Location (city name or lat,lon)
        place: String,

        /// Use AI to triage alerts
        #[arg(long)]
        ai: bool,
    },

    /// Start interactive chat mode
    Chat,

    /// Show worldwide weather snapshot
    World {
        /// Filter for severe weather only
        #[arg(long)]
        severe: bool,
    },
}

fn main() -> Result<()> {
    let cli = Cli::parse();

    // Load configuration
    let config = config::Config::load(cli.offline, cli.debug)?;

    // Handle command
    match cli.command {
        Some(Commands::Story {
            place,
            when,
            horizon,
            focus,
        }) => {
            cli::handle_story(&config, &place, when.as_deref(), &horizon, focus.as_deref(), cli.verbose, cli.json)?;
        }

        Some(Commands::Forecast {
            place,
            when,
            horizon,
            focus,
        }) => {
            cli::handle_forecast(&config, &place, when.as_deref(), &horizon, focus.as_deref(), cli.verbose, cli.json)?;
        }

        Some(Commands::Risk { place, hazards }) => {
            cli::handle_risk(&config, &place, hazards.as_deref(), cli.verbose, cli.json)?;
        }

        Some(Commands::Alerts { place, ai }) => {
            cli::handle_alerts(&config, &place, ai, cli.verbose, cli.json)?;
        }

        Some(Commands::Chat) => {
            cli::handle_chat(&config, cli.verbose)?;
        }

        Some(Commands::World { severe }) => {
            cli::handle_world(&config, severe, cli.verbose, cli.json)?;
        }

        None => {
            if let Some(question) = cli.question {
                cli::handle_question(&config, &question, cli.verbose, cli.json)?;
            } else {
                // No args - default to world view
                cli::handle_world(&config, false, cli.verbose, cli.json)?;
            }
        }
    }

    Ok(())
}
