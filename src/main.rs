use anyhow::Result;
use clap::{Parser, Subcommand};

mod cache;
mod cli;
mod config;
mod fetchers;
mod profile;
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

    /// Generate shell completions
    Completions {
        /// Shell type (bash, zsh, fish, powershell)
        #[arg(value_name = "SHELL")]
        shell: String,
    },

    /// Manage profiles (API keys, preferences, locations)
    #[command(subcommand)]
    Profile(ProfileCommands),
}

#[derive(Subcommand)]
enum ProfileCommands {
    /// Create a new profile
    Create {
        /// Profile name
        name: String,
    },

    /// List all profiles
    List,

    /// Switch to a different profile
    Switch {
        /// Profile name
        name: String,
    },

    /// Show profile details
    Show {
        /// Profile name (defaults to current)
        name: Option<String>,
    },

    /// Delete a profile
    Delete {
        /// Profile name
        name: String,
    },

    /// Set a profile value
    Set {
        /// Field name (gemini_key, openrouter_key, default_location, units)
        field: String,

        /// Value to set
        value: String,
    },

    /// Add a favorite location
    AddFavorite {
        /// Location name
        location: String,
    },

    /// Remove a favorite location
    RemoveFavorite {
        /// Location name
        location: String,
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

        Some(Commands::Completions { shell }) => {
            handle_completions(&shell)?;
        }

        Some(Commands::Profile(profile_cmd)) => {
            handle_profile_command(profile_cmd)?;
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

fn handle_completions(shell: &str) -> Result<()> {
    use clap::CommandFactory;
    use clap_complete::{generate, Shell};
    use std::io;

    let shell = match shell.to_lowercase().as_str() {
        "bash" => Shell::Bash,
        "zsh" => Shell::Zsh,
        "fish" => Shell::Fish,
        "powershell" => Shell::PowerShell,
        _ => {
            eprintln!("Unsupported shell: {}", shell);
            eprintln!("Supported: bash, zsh, fish, powershell");
            std::process::exit(1);
        }
    };

    let mut cmd = Cli::command();
    generate(shell, &mut cmd, "wx", &mut io::stdout());
    Ok(())
}

fn handle_profile_command(cmd: ProfileCommands) -> Result<()> {
    use colored::Colorize;
    use profile::Profile;

    match cmd {
        ProfileCommands::Create { name } => {
            Profile::create(&name)?;
            println!("{} Profile '{}' created", "✓".green(), name.cyan());

            if Profile::list()?.len() == 1 {
                println!("{} Automatically set as active profile", "✓".green());
            }

            println!();
            println!("Set API keys:");
            println!("  {} wx profile set gemini_key YOUR_KEY", "$".dimmed());
            println!("  {} wx profile set openrouter_key YOUR_KEY", "$".dimmed());
        }

        ProfileCommands::List => {
            let profiles = Profile::list()?;
            let current = Profile::get_current_profile_name().unwrap_or_default();

            if profiles.is_empty() {
                println!("No profiles found.");
                println!("Create one with: {} wx profile create <name>", "$".dimmed());
                return Ok(());
            }

            println!();
            println!("{}", "Profiles:".bold());
            for name in profiles {
                let marker = if name == current { "●".green() } else { "○".dimmed() };
                let display_name = if name == current {
                    name.cyan().bold()
                } else {
                    name.normal()
                };
                println!("  {} {}", marker, display_name);
            }
            println!();
            println!("{} = active profile", "●".green());
        }

        ProfileCommands::Switch { name } => {
            Profile::set_current_profile(&name)?;
            println!("{} Switched to profile '{}'", "✓".green(), name.cyan());
        }

        ProfileCommands::Show { name } => {
            let profile = if let Some(name) = name {
                Profile::load(&name)?
            } else {
                Profile::load_current()?
            };

            println!();
            println!("{}", format!("Profile: {}", profile.name).bold().cyan());
            println!("{}", "━".repeat(40).cyan());

            if let Some(loc) = &profile.default_location {
                println!("Default location: {}", loc);
            } else {
                println!("Default location: {}", "none".dimmed());
            }

            println!("Units: {}", profile.units);

            println!();
            println!("API Keys:");
            if let Some(_) = &profile.api_keys.gemini {
                println!("  Gemini: {}", "configured ✓".green());
            } else {
                println!("  Gemini: {}", "not set".dimmed());
            }

            if let Some(_) = &profile.api_keys.openrouter {
                println!("  OpenRouter: {}", "configured ✓".green());
            } else {
                println!("  OpenRouter: {}", "not set".dimmed());
            }

            if !profile.favorites.is_empty() {
                println!();
                println!("Favorites:");
                for fav in &profile.favorites {
                    println!("  • {}", fav);
                }
            }

            println!();
            println!("Created: {}", profile.created_at.dimmed());
        }

        ProfileCommands::Delete { name } => {
            Profile::delete(&name)?;
            println!("{} Profile '{}' deleted", "✓".green(), name);
        }

        ProfileCommands::Set { field, value } => {
            let current_name = Profile::get_current_profile_name()?;
            let mut profile = Profile::load(&current_name)?;

            profile.update(&field, &value)?;
            profile.save()?;

            let display_value = if field.contains("key") {
                format!("{}...", &value.chars().take(8).collect::<String>())
            } else {
                value.clone()
            };

            println!("{} Set {} = {}", "✓".green(), field.cyan(), display_value);
        }

        ProfileCommands::AddFavorite { location } => {
            let current_name = Profile::get_current_profile_name()?;
            let mut profile = Profile::load(&current_name)?;

            profile.add_favorite(&location);
            profile.save()?;

            println!("{} Added '{}' to favorites", "✓".green(), location.cyan());
        }

        ProfileCommands::RemoveFavorite { location } => {
            let current_name = Profile::get_current_profile_name()?;
            let mut profile = Profile::load(&current_name)?;

            profile.remove_favorite(&location);
            profile.save()?;

            println!("{} Removed '{}' from favorites", "✓".green(), location);
        }
    }

    Ok(())
}
