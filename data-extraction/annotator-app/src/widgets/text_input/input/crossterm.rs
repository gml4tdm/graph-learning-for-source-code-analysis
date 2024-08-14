use ratatui::crossterm::event::{Event, KeyCode, KeyEventKind};

use super::command::Command;

impl From<Event> for Command {
    fn from(value: Event) -> Self {
        if let Event::Key(inner) = value {
            match inner.kind {
                KeyEventKind::Press =>  match inner.code {
                    KeyCode::Backspace => Command::DeleteCharacter,
                    KeyCode::Enter => Command::Submit,
                    KeyCode::Left => Command::CursorLeft,
                    KeyCode::Right => Command::CursorRight,
                    KeyCode::Char(c) => Command::InsertCharacter(c),
                    KeyCode::Esc => Command::Cancel,
                    _ => Command::NoAction
                }
                _ => Command::NoAction
            }
        } else {
            Command::NoAction
        }
    }
}
