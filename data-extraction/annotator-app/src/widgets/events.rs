use ratatui::crossterm::event::{KeyEventKind, KeyModifiers};


#[derive(Debug, Copy, Clone, PartialEq, Eq)]
pub enum CommonEvent {
    Null,
    KeyboardPressEvent {
        key: Key,
        // Note that we deliberately omit other modifiers 
        shift: bool,
        alt: bool,
        ctrl: bool
    }
}


#[derive(Debug, Copy, Clone, PartialEq, Eq)]
pub enum Key {
    Char(char),
    F(u8),
    Tab,
    CapsLock,
    //LeftShift,
    //LeftControl,
    //LeftAlt,
    //RightShift,
    //RightControl,
    //RightAlt,
    Enter,
    Escape,
    Backspace,
    Up,
    Down,
    Left,
    Right,
    //Meta,
    Insert,
    Home,
    End,
    PageUp,
    PageDown,
    Delete,
    NumLock,
    Null
}


impl From<ratatui::crossterm::event::Event> for CommonEvent {
    fn from(value: ratatui::crossterm::event::Event) -> Self {
        match value {
            ratatui::crossterm::event::Event::Key(event) if event.kind == KeyEventKind::Press => {
                let key = match event.code {
                    ratatui::crossterm::event::KeyCode::Char(c) => Key::Char(c),
                    ratatui::crossterm::event::KeyCode::F(f) => Key::F(f),
                    ratatui::crossterm::event::KeyCode::Tab => Key::Tab,
                    ratatui::crossterm::event::KeyCode::CapsLock => Key::CapsLock,
                    ratatui::crossterm::event::KeyCode::Enter => Key::Enter,
                    ratatui::crossterm::event::KeyCode::Esc => Key::Escape,
                    ratatui::crossterm::event::KeyCode::Backspace => Key::Backspace,
                    ratatui::crossterm::event::KeyCode::Up => Key::Up,
                    ratatui::crossterm::event::KeyCode::Down => Key::Down,
                    ratatui::crossterm::event::KeyCode::Left => Key::Left,
                    ratatui::crossterm::event::KeyCode::Right => Key::Right,
                    ratatui::crossterm::event::KeyCode::Insert => Key::Insert,
                    ratatui::crossterm::event::KeyCode::Home => Key::Home,
                    ratatui::crossterm::event::KeyCode::End => Key::End,
                    ratatui::crossterm::event::KeyCode::PageUp => Key::PageUp,
                    ratatui::crossterm::event::KeyCode::PageDown => Key::PageDown,
                    ratatui::crossterm::event::KeyCode::Delete => Key::Delete,
                    ratatui::crossterm::event::KeyCode::NumLock => Key::NumLock,
                    _ => Key::Null
                };
                Self::KeyboardPressEvent {
                    key,
                    shift: event.modifiers.contains(KeyModifiers::SHIFT),
                    alt: event.modifiers.contains(KeyModifiers::ALT),
                    ctrl: event.modifiers.contains(KeyModifiers::CONTROL)
                }
            },
            _ => Self::Null
        }
    }
}
