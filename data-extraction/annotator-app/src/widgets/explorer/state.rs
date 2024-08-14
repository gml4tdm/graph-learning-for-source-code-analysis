use std::cmp::Ordering;
use std::fs;
use std::path::{Path, PathBuf};

use ratatui::widgets::TableState;
use crate::widgets::text_input::TextInputState;
//////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////
// File Information Structs
//////////////////////////////////////////////////////////////////////////////////////////////////

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FileInformation {
    pub(super) file_type: FileType,
    pub(super) name: String,
}

impl Ord for FileInformation {
    fn cmp(&self, other: &Self) -> Ordering {
        match self.file_type.cmp(&other.file_type) {
            Ordering::Equal => self.name.cmp(&other.name),
            o => o
        }
    }
}

impl PartialOrd for FileInformation {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

#[derive(Debug, PartialEq, Eq, Copy, Clone)]
pub(super) enum FileType {
    File,
    Directory,
    FileSymlink,
    DirectorySymlink
}

impl FileType {
    pub(super) fn is_symlink(&self) -> bool {
        matches!(self, FileType::FileSymlink | FileType::DirectorySymlink)
    }

    pub(super) fn is_dir(&self) -> bool {
        matches!(self, FileType::Directory | FileType::DirectorySymlink)
    }

    pub(super) fn is_file(&self) -> bool {
        matches!(self, FileType::File | FileType::FileSymlink)
    }
}

impl Ord for FileType {
    fn cmp(&self, other: &Self) -> Ordering {
        match (self, other) {
            (x, y) if x == y => Ordering::Equal,
            (FileType::File, _) => Ordering::Less,
            (_, FileType::File) => Ordering::Greater,
            (FileType::FileSymlink, _) => Ordering::Less,
            (_, FileType::FileSymlink) => Ordering::Greater,
            (FileType::Directory, _) => Ordering::Less,
            (_, FileType::Directory) => Ordering::Greater,
            (FileType::DirectorySymlink, _) => Ordering::Less
        }
    }
}

impl PartialOrd for FileType {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

//////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////
// File Explorer State
//////////////////////////////////////////////////////////////////////////////////////////////////

pub struct FileExplorerState {
    pub(super) table_state: TableState,
    pub(super) directory: PathBuf,
    pub(super) files: Vec<FileInformation>,
    pub(super) io_error: Option<String>,
    pub(super) filename_input_state: Option<TextInputState>
}


impl FileExplorerState {
    pub fn new(directory: PathBuf) -> anyhow::Result<Self> {
        let (files, table_state, io_error) = match Self::fresh_state(&directory) {
            Ok(res) => (res.0, res.1, None),
            Err(e) => (Vec::new(), TableState::default(), Some(e.to_string()))
        };
        Ok(Self { table_state, directory, files, io_error, filename_input_state: None })
    }

    pub fn cwd() -> anyhow::Result<Self> {
        let directory = std::env::current_dir()?;
        Self::new(directory)
    }

    pub(super) fn update_directory(&mut self, path: PathBuf) -> anyhow::Result<()> {
        match Self::fresh_state(&path) {
            Ok((files, table_state)) => {
                self.directory = path;
                self.files = files;
                self.table_state = table_state;
                //self.io_error = None;
                Ok(())
            }
            Err(e) => {
                self.io_error = Some(e.to_string());
                Ok(())
            }
        }
    }
    
    fn fresh_state(path: &Path) -> anyhow::Result<(Vec<FileInformation>, TableState)> {
        let mut files = Self::collect_files(path)?;
        files.sort();
        let table_state = TableState::new()
            .with_selected(0)
            .with_offset(0);
        Ok((files, table_state))
    }

    fn collect_files(path: &Path) -> anyhow::Result<Vec<FileInformation>> {
        let mut files = Vec::new();
        for entry in fs::read_dir(path)? {
            let entry = entry?;
            let metadata = entry.metadata()?;
            let file_type = if metadata.is_file() {
                FileType::File
            } else if metadata.is_dir() {
                FileType::Directory
            } else {
                assert!(metadata.is_symlink());
                let symlink_metadata = fs::metadata(entry.path())?;
                if symlink_metadata.is_file() {
                    FileType::FileSymlink
                } else {
                    assert!(symlink_metadata.is_dir());
                    FileType::DirectorySymlink
                }
            };
            let name = entry.file_name()
                .into_string()
                .expect("Failed to convert filename");
            files.push(FileInformation { file_type, name });
        }
        Ok(files)
    }
}
