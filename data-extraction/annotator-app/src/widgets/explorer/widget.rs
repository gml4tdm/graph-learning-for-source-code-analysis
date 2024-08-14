use std::path::PathBuf;

use ratatui::buffer::Buffer;
use ratatui::crossterm::event::Event;
use ratatui::layout::Rect;
use ratatui::widgets::{StatefulWidget, StatefulWidgetRef};

use crate::widgets::text_input::{TextInput, TextInputEvent, TextInputState};
use super::state::FileExplorerState;
use super::state::FileType;
use super::input::Command;

#[derive(Debug, Copy, Clone)]
pub struct FileExplorer {
    dialog_type: FileDialogType
}

#[allow(clippy::enum_variant_names)]
#[derive(Debug, Copy, Clone, Eq, PartialEq)]
pub enum FileDialogType {
    AskFilename,
    AskDirectory,
    AskSaveAsFilename
}

impl FileDialogType {
    pub(super) fn show_filenames(&self) -> bool {
        match self {
            FileDialogType::AskFilename => true,
            FileDialogType::AskDirectory => false,
            FileDialogType::AskSaveAsFilename => true
        }
    }
    
    pub(super) fn allow_selecting_directory(&self) -> bool {
        match self {
            FileDialogType::AskFilename => false,
            FileDialogType::AskDirectory => true,
            FileDialogType::AskSaveAsFilename => false
        }
    }
    
    pub(super) fn allow_selecting_files(&self) -> bool {
        match self {
            FileDialogType::AskFilename => true,
            FileDialogType::AskDirectory => false,
            FileDialogType::AskSaveAsFilename => true
        }
    }
}


#[derive(Debug, Clone, Eq, PartialEq)]
pub enum FileExplorerEvent {
    Selecting,
    Selected(PathBuf),
    Cancelled
}

#[allow(unused)]
impl FileExplorer {
    pub fn new(dialog_type: FileDialogType) -> Self {
        Self{dialog_type}
    }
    
    pub fn cursor(&self, area: Rect, state: &FileExplorerState) -> Option<(u16, u16)> {
        let render = super::ui::FileExplorerRenderer::new(area, self.dialog_type, state);
        render.cursor()
    }

    pub fn handle_events(&self,
                         event: Event,
                         state: &mut FileExplorerState) -> anyhow::Result<FileExplorerEvent> {
        if let Some(ref mut inner_state) = state.filename_input_state {
            match TextInput::new().handle_events(event, inner_state) {
                TextInputEvent::Typing => Ok(FileExplorerEvent::Selecting),
                TextInputEvent::Cancel => {
                    // Set the state to None to stop typing 
                    state.filename_input_state = None;
                    Ok(FileExplorerEvent::Selecting)
                },
                TextInputEvent::Typed(filename) => {
                    let full_path = state.directory.join(filename);
                    Ok(FileExplorerEvent::Selected(full_path))
                }
            }
        } else {
            let command = event.into();
            if command != Command::NoAction {
                let _ = state.io_error.take();      // Reset error on key action
            }
            match command {
                Command::ArrowUp => self.move_arrow_up(state),
                Command::ArrowDown => self.move_arrow_down(state),
                Command::DirectoryUp => self.move_directory_up(state),
                Command::DirectoryDown => self.move_directory_down(state),
                Command::Confirm => self.get_selected_file(state),
                Command::EnterFileName => {
                    // Setting the state will also update the ui 
                    state.filename_input_state = Some(TextInputState::new());
                    Ok(FileExplorerEvent::Selecting)
                },
                Command::Exit => Ok(FileExplorerEvent::Cancelled),
                Command::NoAction => Ok(FileExplorerEvent::Selecting)
            }
        }
    }
    
    fn move_arrow_up(&self, state: &mut FileExplorerState) -> anyhow::Result<FileExplorerEvent> {
        let sel =  state.table_state.selected().unwrap();
        if sel > 0 {
            state.table_state.select(Some(sel - 1));
        }
        Ok(FileExplorerEvent::Selecting)
    }
    
    fn move_arrow_down(&self, state: &mut FileExplorerState) -> anyhow::Result<FileExplorerEvent> {
        let sel =  state.table_state.selected().unwrap();
        if sel + 1 < state.files.len() {
            state.table_state.select(Some(sel + 1));
        }
        Ok(FileExplorerEvent::Selecting)
    }
    
    fn move_directory_up(&self, state: &mut FileExplorerState) -> anyhow::Result<FileExplorerEvent> {
        if let Some(parent) = state.directory.parent() {
            let old = state.directory.file_name()
                .expect("Failed to get filename")
                .to_os_string()
                .into_string()
                .expect("Failed to convert filename");
            state.update_directory(parent.to_path_buf())?;
            let index = state.files.iter().enumerate()
                .find(|(_, info)| info.name == old)
                .expect("Failed to find file index");
            state.table_state.select(Some(index.0));
        }
        Ok(FileExplorerEvent::Selecting)
    }
    
    fn move_directory_down(&self, state: &mut FileExplorerState) -> anyhow::Result<FileExplorerEvent> {
        let sel =  state.table_state.selected().unwrap();
        let info = state.files.get(sel).unwrap();
        if info.file_type == FileType::Directory {
            let path = state.directory.join(info.name.clone());
            state.update_directory(path)?;
        }
        Ok(FileExplorerEvent::Selecting)
    }
    
    fn get_selected_file(&self, state: &mut FileExplorerState) -> anyhow::Result<FileExplorerEvent> {
        let sel =  state.table_state.selected().unwrap();
        let info = state.files.get(sel).unwrap();
        if info.file_type.is_dir() && !self.dialog_type.allow_selecting_directory() {
            return Ok(FileExplorerEvent::Selecting)
        }
        if info.file_type.is_file() && !self.dialog_type.allow_selecting_files() {
            return Ok(FileExplorerEvent::Selecting)
        }
        let path = state.directory.join(info.name.clone());
        Ok(FileExplorerEvent::Selected(path))
    }
}


impl StatefulWidgetRef for FileExplorer {
    type State = FileExplorerState;

    fn render_ref(&self, area: Rect, buf: &mut Buffer, state: &mut Self::State) {
        super::ui::FileExplorerRenderer::new(area, self.dialog_type, state).render(buf, state);
    }
}

impl StatefulWidget for &FileExplorer {
    type State = FileExplorerState;

    fn render(self, area: Rect, buf: &mut Buffer, state: &mut Self::State) {
        <FileExplorer as StatefulWidgetRef>::render_ref(self, area, buf, state);
    }
}


