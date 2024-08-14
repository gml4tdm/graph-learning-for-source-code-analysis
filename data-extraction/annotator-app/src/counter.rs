use std::collections::hash_map::Entry;
use std::collections::HashMap;
use std::hash::Hash;


pub struct Counter<T>(HashMap<T, i32>);


impl<T> Counter<T> {
    pub fn new() -> Self {
        Self(HashMap::new())
    }
}

#[allow(unused)]
impl<T: Hash + Eq> Counter<T> {
    pub fn count(&self, item: &T) -> Option<i32> {
        self.0.get(item).copied()
    }

    pub fn add(&mut self, item: T) -> i32 {
        self.update_by(item, 1)
    }
    
    pub fn delete(&mut self, item: &T) -> Option<i32> {
        self.0.remove(item)
    }
    
    pub fn len(&self) -> usize {
        self.0.len()
    }
    
    pub fn update_by(&mut self, item: T, amount: i32) -> i32 {
        match self.0.entry(item) {
            Entry::Occupied(mut e) => {
                *e.get_mut() += amount;
                *e.get()
            }
            Entry::Vacant(e) => {
                e.insert(amount);
                amount
            }
        }
    }
    
    pub fn iter(&self) -> impl Iterator<Item=(&T, i32)> {
        self.0.iter().map(|(k, v)| (k, *v))
    }
}

impl<T: Hash + Eq, R: Iterator<Item=T>> From<R> for Counter<T> {
    fn from(value: R) -> Self {
        let mut counter = Self::new();
        for item in value {
            let _ = counter.add(item);
        }
        counter
    }
}
