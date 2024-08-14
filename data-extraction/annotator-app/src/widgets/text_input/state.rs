pub struct TextInputState {
    pub(super) input: Vec<char>,
    pub(super) cursor: u16
}

impl TextInputState {
    pub fn new() -> Self {
        Self {
            input: Vec::new(),
            cursor: 0
        }
    }
    
    pub fn clear(&mut self) {
        self.input.clear();
        self.cursor = 0;
    }
    
    pub fn set_input(&mut self, input: String) {
        self.input = input.chars().collect();
        self.cursor = self.input.len() as u16;
    }
    
    pub(super) fn cursor_left(&mut self) {
        if self.cursor > 0 {
            self.cursor -= 1;
        }
    }

    pub(super) fn cursor_right(&mut self) {
        if self.cursor < self.input.len() as u16 {
            self.cursor += 1;
        }
    }

    pub(super) fn backspace(&mut self) {
        if self.cursor > 0 {
            self.input.remove(self.cursor as usize - 1);
            self.cursor -= 1;
        }
    }

    pub(super) fn insert(&mut self, c: char) {
        self.input.insert(self.cursor as usize, c);
        self.cursor += 1;
    }
    
    pub fn get_input(&self) -> String {
        self.input.iter().collect()
    }
}
