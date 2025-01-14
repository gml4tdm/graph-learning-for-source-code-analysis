use std::path::PathBuf;

use ratatui::backend::Backend;
use ratatui::{Frame, Terminal};
use ratatui::crossterm::event;
use ratatui::crossterm::event::{Event, KeyCode};
use ratatui::layout::Alignment;
use ratatui::prelude::Widget;
use ratatui::text::Line;
use ratatui::widgets::{Block, TableState};
use ratatui::widgets::block::{Position, Title};
use ratatui::style::Stylize;
use ratatui::symbols::border;

use crate::config::Config;
use crate::counter::Counter;
use crate::data::{RefinementAction, RefinementData};
use crate::editor::{draw_editor, EditorEvent, handle_editor_events, index_to_string, init_tree_view_state};
use crate::viewer::TreeViewState;
use crate::widgets::explorer::{FileDialogType, FileExplorer, FileExplorerEvent, FileExplorerState};
use crate::widgets::text_input::TextInputState;

pub struct App {
    state: AppState 
}

pub enum AppState {
    Welcome,
    SelectingNew,
    SelectingExisting{
        explorer_state: FileExplorerState
    },
    Editing{
        project_file: PathBuf, 
        data: RefinementData,
        counter: Counter<String>,
        table_state: TableState,
        annotation_state: Option<(usize, Vec<TextInputState>)>,
        goto_state: Option<TextInputState>,
        view_state: Option<TreeViewState>
    },
    Quit
}

impl App {
    pub fn new() -> Self {
        Self{state: AppState::Welcome}
    }
    
    pub fn mainloop<B: Backend>(mut self,
                                terminal: &mut Terminal<B>) -> anyhow::Result<()> {
        let config_path = PathBuf::from("config.json");
        let mut config = Config::load_or_default(&config_path)?;
        loop {
            match self.state {
                AppState::Welcome => {
                    terminal.draw(render_welcome)?;
                    if let Some(s) = handle_events_welcome(&config)? {
                        self.state = s;
                    }
                }
                AppState::SelectingNew => {}
                AppState::SelectingExisting{ref mut explorer_state} => {
                    if let Some(s) = handle_existing_project_selection(terminal, explorer_state, &mut config)? {
                        config.store(&config_path)?;
                        self.state = s;
                    }
                }
                AppState::Editing {
                    ref project_file, 
                    ref mut data, 
                    ref mut counter,
                    ref mut table_state,
                    ref mut annotation_state,
                    ref mut goto_state, 
                    ref mut view_state
                } => {
                    terminal.draw(|f| {
                        draw_editor(f, counter, data.locked.as_mut().unwrap(), table_state, annotation_state, goto_state, view_state);
                    })?;
                    match handle_editor_events(event::read()?, counter, data.refinements().to_vec(), 
                                               data.locked.as_mut().unwrap(), table_state, 
                                               annotation_state, goto_state, view_state) {
                        EditorEvent::RedrawTree(old, new) => {
                            data.insert_refinement(old, new);
                            data.store_to_file(project_file).expect("Save failed");
                            let old = view_state.take().unwrap();
                            let new = init_tree_view_state(counter, data.refinements().to_vec());
                            let _ = view_state.insert(TreeViewState::from_tree_and_state(new, old));
                        }
                        EditorEvent::Exit => {
                            self.state = AppState::Welcome;
                        },
                        EditorEvent::Edit {old, new} => {
                            let old = index_to_string(counter, old);
                            if new.len() == 1 {
                                data.update_refine(counter, old, new[0].clone())
                                    .expect("Error updating refinement");
                            } else if new.len() == 2 {
                                data.update_split(counter, old, new[0].clone(), new[1].clone())
                                    .expect("Error updating split");
                            } else {
                                data.update_n_ary_split(counter, old, new)
                                    .expect("Error updating n-ary split");
                            }
                            data.store_to_file(project_file).expect("Save failed");
                        },
                        EditorEvent::LockToggle => {
                            data.store_to_file(project_file).expect("Save failed");
                        }
                        _ => {}
                    }
                    
                }
                AppState::Quit => {
                    break;
                }
            }
        }
        Ok(())
    }
}

//////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////
// Welcome Screen
//////////////////////////////////////////////////////////////////////////////////////////////////

fn render_welcome(frame: &mut Frame) {
    let instructions = Title::from(
        Line::from(
            vec![
                // " New Project ".into(),
                // "<n>".blue().bold(),
                " Open Project ".into(),
                "<o>".blue().bold(),
                " Exit ".into(),
                "<q> ".blue().bold(),
            ]
        )
    );
    let block = Block::bordered()
        .title(Title::from(" Annotator App ".bold()).alignment(Alignment::Center))
        .title(instructions.alignment(Alignment::Center).position(Position::Bottom))
        .border_set(border::THICK);
    block.render(frame.size(), frame.buffer_mut());
}

fn handle_events_welcome(config: &Config) -> anyhow::Result<Option<AppState>> {
    let event = ratatui::crossterm::event::read()?;
    if let Event::Key(inner) = event {
        match inner.code {
            KeyCode::Char('q') => { 
                return Ok(Some(AppState::Quit));
            }
            // KeyCode::Char('n') => {
            //     return Ok(Some(AppState::Quit));
            // }
            KeyCode::Char('o') => {
                let explorer_state = if let Some(path) = config.last_file_directory.clone() {
                    FileExplorerState::new(PathBuf::from(path))?
                } else {
                    FileExplorerState::cwd()?
                };
                return Ok(Some(AppState::SelectingExisting{explorer_state}));
            }
            _ => {}
        }
    }
    Ok(None)
}

//////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////
// Selecting an existing project
//////////////////////////////////////////////////////////////////////////////////////////////////


fn handle_existing_project_selection<B: Backend>(
    terminal: &mut Terminal<B>, 
    explorer_state: &mut FileExplorerState, 
    config: &mut Config) -> anyhow::Result<Option<AppState>> 
{
    let explorer = FileExplorer::new(FileDialogType::AskFilename);
    
    terminal.draw(
        |f| {
            f.render_stateful_widget(&explorer, f.size(), explorer_state);
            if let Some((x, y)) = explorer.cursor(f.size(), explorer_state) {
                f.set_cursor(x, y);
            }
        }
    )?;
    
    let state = explorer.handle_events(
        ratatui::crossterm::event::read()?,
        explorer_state
    )?;
    match state {
        FileExplorerEvent::Selecting => {
            Ok(None)
        }
        FileExplorerEvent::Selected(path) => {
            config.last_file_directory = Some(
                path.parent()
                    .unwrap()
                    .to_path_buf()
                    .into_os_string()
                    .into_string()
                    .expect("Failed to convert path")
            );
            let result = RefinementData::load_from_file(path.as_path());
            match result {
                Ok(data) => {
                    let actions = data.refinements().to_vec();
                    let result = data.get_refined();
                    if let Ok(counter) = result {
                        let state = AppState::Editing {
                            project_file: path,
                            data,
                            counter,
                            table_state: TableState::default().with_selected(0),
                            annotation_state: None,
                            goto_state: None,
                            view_state: None
                        };
                        Ok(Some(state))
                    } else {
                        //panic!("E: {}", result.err().unwrap());
                        Ok(Some(AppState::Welcome))
                    }
                }
                Err(_e) => {
                    Ok(Some(AppState::Welcome))
                }
            }
        }
        FileExplorerEvent::Cancelled => {
            Ok(Some(AppState::Welcome))
        }
    }
}