//! Minimal checked-arithmetic example for demonstrating OSQAr links.
//!
//! This crate is not a qualified safety component. A real project must tailor
//! requirements, target assumptions, verification, and toolchain controls.

/// Errors returned by the example arithmetic operations.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ArithmeticError {
    NotInitialized,
    Overflow,
}

/// Small stateful component used by the example requirements and tests.
#[derive(Debug, Default)]
pub struct Component {
    initialized: bool,
}

impl Component {
    /// Creates a component in its inactive state.
    #[must_use]
    pub const fn new() -> Self {
        Self { initialized: false }
    }

    /// Enables arithmetic operations. Calling this repeatedly is harmless.
    pub fn initialize(&mut self) {
        self.initialized = true;
    }

    /// Disables arithmetic operations.
    pub fn deinitialize(&mut self) {
        self.initialized = false;
    }

    /// Adds two values while detecting signed overflow.
    pub fn checked_add(&self, left: i32, right: i32) -> Result<i32, ArithmeticError> {
        if !self.initialized {
            return Err(ArithmeticError::NotInitialized);
        }
        left.checked_add(right).ok_or(ArithmeticError::Overflow)
    }

    /// Subtracts two values while detecting signed overflow.
    pub fn checked_sub(&self, left: i32, right: i32) -> Result<i32, ArithmeticError> {
        if !self.initialized {
            return Err(ArithmeticError::NotInitialized);
        }
        left.checked_sub(right).ok_or(ArithmeticError::Overflow)
    }
}

#[cfg(test)]
mod tests {
    use super::{ArithmeticError, Component};

    #[test]
    fn operations_require_initialization() {
        let component = Component::new();
        assert_eq!(
            component.checked_add(1, 2),
            Err(ArithmeticError::NotInitialized)
        );
    }

    #[test]
    fn checked_operations_return_nominal_results() {
        let mut component = Component::new();
        component.initialize();
        assert_eq!(component.checked_add(10, 20), Ok(30));
        assert_eq!(component.checked_sub(50, 20), Ok(30));
    }

    #[test]
    fn checked_operations_detect_overflow() {
        let mut component = Component::new();
        component.initialize();
        assert_eq!(
            component.checked_add(i32::MAX, 1),
            Err(ArithmeticError::Overflow)
        );
        assert_eq!(
            component.checked_sub(i32::MIN, 1),
            Err(ArithmeticError::Overflow)
        );
    }

    #[test]
    fn deinitialization_disables_operations() {
        let mut component = Component::new();
        component.initialize();
        component.deinitialize();
        assert_eq!(
            component.checked_add(1, 2),
            Err(ArithmeticError::NotInitialized)
        );
    }
}
