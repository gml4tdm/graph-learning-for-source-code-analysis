#[derive(Debug, Copy, Clone, PartialEq, Eq)]
pub enum Command {
    ArrowUp,
    ArrowDown,
    DirectoryUp,
    DirectoryDown,
    Exit,
    Confirm,
    EnterFileName,
    NoAction
}
