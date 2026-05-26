cmake_minimum_required(VERSION 3.16)
project(osqar_asil_d_c C)

# ── Compiler settings for ASIL D safety library ──
set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)

# Reproducible build support
if(DEFINED ENV{SOURCE_DATE_EPOCH})
    set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -DSOURCE_DATE_EPOCH=$ENV{SOURCE_DATE_EPOCH}")
endif()

# Safety-critical compiler flags (ISO 26262-6 §8.4, Table 7)
set(SAFETY_FLAGS
    -Wall -Wextra -Wpedantic -Werror
    -Wconversion -Wshadow -Wstrict-prototypes
    -Wmissing-prototypes -Wmissing-declarations
    -fno-strict-aliasing
    -fstack-protector-strong
    -D_FORTIFY_SOURCE=2
)

# Debug / sanitizer build type
set(CMAKE_C_FLAGS_DEBUG "${CMAKE_C_FLAGS_DEBUG} -fsanitize=address,undefined -fno-omit-frame-pointer")

# Coverage build type
set(CMAKE_C_FLAGS_COVERAGE "${CMAKE_C_FLAGS_COVERAGE} -fprofile-arcs -ftest-coverage -O0")

# ── Library target ──
add_library(osqar_asil_d STATIC src/project.c)
target_include_directories(osqar_asil_d PUBLIC include)
target_compile_options(osqar_asil_d PRIVATE ${SAFETY_FLAGS})

# ── Test target ──
add_executable(osqar_asil_d_tests tests/test_project.c)
target_link_libraries(osqar_asil_d_tests PRIVATE osqar_asil_d)
target_compile_options(osqar_asil_d_tests PRIVATE ${SAFETY_FLAGS})

# ── Test runner ──
enable_testing()
add_test(NAME asil_d_unit_tests COMMAND osqar_asil_d_tests)

# ── Coverage target ──
add_custom_target(coverage
    COMMAND ${CMAKE_COMMAND} -E echo "Coverage requires: cmake -DCMAKE_BUILD_TYPE=Coverage .. && make && ctest && gcovr"
)
