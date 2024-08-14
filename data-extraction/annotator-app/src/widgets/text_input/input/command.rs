#[derive(Debug, Copy, Clone, PartialEq, Eq)]
pub enum Command {
    CursorLeft,
    CursorRight,
    Submit,
    Cancel,
    DeleteCharacter,
    InsertCharacter(char),
    NoAction
}