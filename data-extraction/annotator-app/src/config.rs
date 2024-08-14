use std::path::Path;

#[derive(Debug, serde::Deserialize, serde::Serialize)]
pub struct Config {
    pub last_file_directory: Option<String>
}


impl Config {
    pub fn new() -> Self {
        Self {
            last_file_directory: None
        }
    }
    
    pub fn load(path: &Path) -> anyhow::Result<Self> {
        let file = std::fs::File::open(&path)?;
        let config: Config = serde_json::from_reader(file)?;
        Ok(config)
    }
    
    pub fn load_or_default(path: &Path) -> anyhow::Result<Self> {
        if !path.exists() {
            Self::new().store(path)?;
        }
        Self::load(path)
    }
    
    pub fn store(&self, path: &Path) -> anyhow::Result<()> {
        let file = std::fs::File::create(path)?;
        serde_json::to_writer_pretty(file, self)?;
        Ok(())
    }
}
