#include "osqar_shared.h"

int osqar_shared_magic(void) {
    return 42;
}

int osqar_shared_add(int a, int b) {
    return a + b;
}
