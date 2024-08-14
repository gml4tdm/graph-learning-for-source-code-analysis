use ratatui::crossterm::event::{Event, KeyCode, KeyEventKind};

use super::command::Command;

impl From<Event> for Command {
    fn from(value: Event) -> Self {
        if let Event::Key(inner) = value {
            match inner.kind {
                KeyEventKind::Press =>  match inner.code {
                    KeyCode::Up => Command::ArrowUp,
                    KeyCode::Down => Command::ArrowDown,
                    KeyCode::Left => Command::DirectoryUp,
                    KeyCode::Right => Command::DirectoryDown,
                    KeyCode::Enter => Command::Confirm,
                    KeyCode::Esc => Command::Exit,
                    KeyCode::Char('n') => Command::EnterFileName,
                    _ => Command::NoAction
                }
                _ => Command::NoAction
            }
        } else {
            Command::NoAction
        }
    }
}
