use std::env;
use std::time::Duration;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Config {
    pub scylla_uri: String,
    pub keyspace: String,
    pub request_timeout: Duration,
}

impl Config {
    pub fn from_env() -> Self {
        Self {
            scylla_uri: read_env("SCYLLA_URI", "127.0.0.1:9042"),
            keyspace: read_env("SCYLLA_KEYSPACE", "demo"),
            request_timeout: read_timeout_secs("SCYLLA_REQUEST_TIMEOUT_SECS", 10),
        }
    }
}

fn read_env(key: &str, default: &str) -> String {
    env::var(key).unwrap_or_else(|_| default.to_string())
}

fn read_timeout_secs(key: &str, default: u64) -> Duration {
    let secs = env::var(key)
        .ok()
        .and_then(|value| value.parse::<u64>().ok())
        .filter(|secs| *secs > 0)
        .unwrap_or(default);

    Duration::from_secs(secs)
}

#[cfg(test)]
mod tests {
    use super::Config;
    use std::time::Duration;

    #[test]
    fn from_env_should_use_defaults_when_env_is_missing() {
        let config = Config::from_env();

        assert_eq!(config.scylla_uri, "127.0.0.1:9042");
        assert_eq!(config.keyspace, "demo");
        assert_eq!(config.request_timeout, Duration::from_secs(10));
    }
}
