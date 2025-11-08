use anyhow::{Result, anyhow};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::fs;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Profile {
    pub name: String,
    pub default_location: Option<String>,
    pub api_keys: ApiKeys,
    pub units: String,
    pub favorites: Vec<String>,
    pub created_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ApiKeys {
    pub gemini: Option<String>,
    pub openrouter: Option<String>,
}

impl Profile {
    /// Create a new profile
    pub fn new(name: &str) -> Self {
        Profile {
            name: name.to_string(),
            default_location: None,
            api_keys: ApiKeys {
                gemini: None,
                openrouter: None,
            },
            units: "imperial".to_string(),
            favorites: vec![],
            created_at: chrono::Utc::now().to_rfc3339(),
        }
    }

    /// Get profiles directory path
    pub fn profiles_dir() -> Result<PathBuf> {
        let home = std::env::var("HOME")
            .or_else(|_| std::env::var("USERPROFILE"))
            .map_err(|_| anyhow!("Could not determine home directory"))?;

        let profiles_dir = PathBuf::from(home).join(".wx").join("profiles");
        fs::create_dir_all(&profiles_dir)?;
        Ok(profiles_dir)
    }

    /// Get path to profile file
    pub fn profile_path(name: &str) -> Result<PathBuf> {
        let profiles_dir = Self::profiles_dir()?;
        Ok(profiles_dir.join(format!("{}.json", name)))
    }

    /// Get path to current profile marker
    fn current_profile_path() -> Result<PathBuf> {
        let profiles_dir = Self::profiles_dir()?;
        Ok(profiles_dir.join(".current"))
    }

    /// Load a profile by name
    pub fn load(name: &str) -> Result<Self> {
        let path = Self::profile_path(name)?;
        if !path.exists() {
            return Err(anyhow!("Profile '{}' not found", name));
        }

        let contents = fs::read_to_string(&path)?;
        let profile: Profile = serde_json::from_str(&contents)?;
        Ok(profile)
    }

    /// Load the currently active profile
    pub fn load_current() -> Result<Self> {
        let current_name = Self::get_current_profile_name()?;
        Self::load(&current_name)
    }

    /// Save profile to disk
    pub fn save(&self) -> Result<()> {
        let path = Self::profile_path(&self.name)?;
        let json = serde_json::to_string_pretty(self)?;
        fs::write(&path, json)?;
        Ok(())
    }

    /// Create and save a new profile
    pub fn create(name: &str) -> Result<Self> {
        // Validate name
        if name.is_empty() || name.contains('/') || name.contains('\\') {
            return Err(anyhow!("Invalid profile name: '{}'", name));
        }

        // Check if already exists
        let path = Self::profile_path(name)?;
        if path.exists() {
            return Err(anyhow!("Profile '{}' already exists", name));
        }

        // Create and save
        let profile = Profile::new(name);
        profile.save()?;

        // If no current profile exists, or current profile doesn't exist, make this the current one
        let current_path = Self::current_profile_path()?;
        if !current_path.exists() {
            Self::set_current_profile(name)?;
        } else {
            // Check if current profile actually exists
            let current_name = Self::get_current_profile_name().unwrap_or_default();
            if !Self::exists(&current_name) {
                Self::set_current_profile(name)?;
            }
        }

        Ok(profile)
    }

    /// List all profiles
    pub fn list() -> Result<Vec<String>> {
        let profiles_dir = Self::profiles_dir()?;
        let mut profiles = Vec::new();

        for entry in fs::read_dir(&profiles_dir)? {
            let entry = entry?;
            let path = entry.path();

            if path.is_file() && path.extension().and_then(|s| s.to_str()) == Some("json") {
                if let Some(name) = path.file_stem().and_then(|s| s.to_str()) {
                    profiles.push(name.to_string());
                }
            }
        }

        profiles.sort();
        Ok(profiles)
    }

    /// Delete a profile
    pub fn delete(name: &str) -> Result<()> {
        let path = Self::profile_path(name)?;

        if !path.exists() {
            return Err(anyhow!("Profile '{}' not found", name));
        }

        // Don't allow deleting the current profile
        if let Ok(current) = Self::get_current_profile_name() {
            if current == name {
                return Err(anyhow!(
                    "Cannot delete active profile '{}'. Switch to another profile first.",
                    name
                ));
            }
        }

        fs::remove_file(&path)?;
        Ok(())
    }

    /// Get current profile name
    pub fn get_current_profile_name() -> Result<String> {
        let path = Self::current_profile_path()?;

        if !path.exists() {
            return Err(anyhow!("No active profile set"));
        }

        let name = fs::read_to_string(&path)?;
        Ok(name.trim().to_string())
    }

    /// Set current profile
    pub fn set_current_profile(name: &str) -> Result<()> {
        // Verify profile exists
        let profile_path = Self::profile_path(name)?;
        if !profile_path.exists() {
            return Err(anyhow!("Profile '{}' does not exist", name));
        }

        // Write current profile name
        let path = Self::current_profile_path()?;
        fs::write(&path, name)?;
        Ok(())
    }

    /// Check if a profile exists
    pub fn exists(name: &str) -> bool {
        Self::profile_path(name)
            .ok()
            .and_then(|p| Some(p.exists()))
            .unwrap_or(false)
    }

    /// Update profile with new values
    pub fn update(&mut self, field: &str, value: &str) -> Result<()> {
        match field {
            "default_location" => {
                self.default_location = Some(value.to_string());
            }
            "gemini_key" => {
                self.api_keys.gemini = Some(value.to_string());
            }
            "openrouter_key" => {
                self.api_keys.openrouter = Some(value.to_string());
            }
            "units" => {
                if value != "imperial" && value != "metric" {
                    return Err(anyhow!("Units must be 'imperial' or 'metric'"));
                }
                self.units = value.to_string();
            }
            _ => {
                return Err(anyhow!("Unknown field: {}", field));
            }
        }
        Ok(())
    }

    /// Add a favorite location
    pub fn add_favorite(&mut self, location: &str) {
        if !self.favorites.contains(&location.to_string()) {
            self.favorites.push(location.to_string());
        }
    }

    /// Remove a favorite location
    pub fn remove_favorite(&mut self, location: &str) {
        self.favorites.retain(|l| l != location);
    }
}
