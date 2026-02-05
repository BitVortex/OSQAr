#include "project.h"

int main(void) {
    return osqar_project_add(1, 1) == 2 ? 0 : 1;
}
