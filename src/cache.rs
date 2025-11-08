use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};

/// Cache entry with timestamp for TTL
#[derive(Debug, Clone, Serialize, Deserialize)]
struct CacheEntry<T> {
    data: T,
    timestamp: u64,
}

/// Persistent cache using Sled
pub struct Cache {
    db: sled::Db,
}

impl Cache {
    /// Open or create cache database
    pub fn open() -> Result<Self> {
        let cache_dir = Self::cache_dir()?;
        let db = sled::open(cache_dir)?;
        Ok(Cache { db })
    }

    /// Get cache directory path
    fn cache_dir() -> Result<PathBuf> {
        let home = std::env::var("HOME")
            .or_else(|_| std::env::var("USERPROFILE"))
            .unwrap_or_else(|_| ".".to_string());

        let cache_dir = PathBuf::from(home).join(".cache").join("wx");
        std::fs::create_dir_all(&cache_dir)?;
        Ok(cache_dir)
    }

    /// Get current timestamp in seconds
    fn now() -> u64 {
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs()
    }

    /// Get value from cache if not expired
    pub fn get<T>(&self, key: &str, ttl_seconds: u64) -> Option<T>
    where
        T: for<'de> Deserialize<'de>,
    {
        let bytes = self.db.get(key).ok()??;
        let entry: CacheEntry<T> = serde_json::from_slice(&bytes).ok()?;

        // Check if expired
        let age = Self::now().saturating_sub(entry.timestamp);
        if age > ttl_seconds {
            // Expired, remove it
            let _ = self.db.remove(key);
            return None;
        }

        Some(entry.data)
    }

    /// Set value in cache
    pub fn set<T>(&self, key: &str, value: T) -> Result<()>
    where
        T: Serialize,
    {
        let entry = CacheEntry {
            data: value,
            timestamp: Self::now(),
        };
        let bytes = serde_json::to_vec(&entry)?;
        self.db.insert(key, bytes)?;
        Ok(())
    }

    /// Remove value from cache
    pub fn remove(&self, key: &str) -> Result<()> {
        self.db.remove(key)?;
        Ok(())
    }

    /// Clear all cache entries
    pub fn clear(&self) -> Result<()> {
        self.db.clear()?;
        Ok(())
    }

    /// Get cache statistics
    pub fn stats(&self) -> CacheStats {
        CacheStats {
            entries: self.db.len(),
            size_bytes: self.db.size_on_disk().unwrap_or(0),
        }
    }
}

#[derive(Debug)]
pub struct CacheStats {
    pub entries: usize,
    pub size_bytes: u64,
}

// Cache key generators
impl Cache {
    /// Generate key for geocoding cache
    pub fn geocode_key(query: &str) -> String {
        format!("geo:{}", query.to_lowercase().trim())
    }

    /// Generate key for weather forecast cache
    pub fn forecast_key(lat: f64, lon: f64) -> String {
        format!("forecast:{:.4},{:.4}", lat, lon)
    }

    /// Generate key for alerts cache
    pub fn alerts_key(lat: f64, lon: f64) -> String {
        format!("alerts:{:.4},{:.4}", lat, lon)
    }
}

// TTL constants (in seconds)
pub const TTL_GEOCODE: u64 = 86400 * 365; // 1 year (locations don't change)
pub const TTL_FORECAST: u64 = 600; // 10 minutes
pub const TTL_ALERTS: u64 = 300; // 5 minutes (critical, stay fresh)
pub const TTL_STORY: u64 = 1800; // 30 minutes
