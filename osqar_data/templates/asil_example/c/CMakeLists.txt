cmake_minimum_required(VERSION 3.16)
project(asil_example_c C)

# ── Example compiler settings (project policy; ASIL D target) ──
set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)

# Reproducible build support
if(DEFINED ENV{SOURCE_DATE_EPOCH})
    set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -DSOURCE_DATE_EPOCH=$ENV{SOURCE_DATE_EPOCH}")
endif()

# OSQAr project-policy compiler flags. ISO 26262-6 §8.4.5 and Table 6
# provide implementation-language/design-principle context; they do not
# mandate this particular compiler option set.
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
add_library(asil_example_c STATIC src/project.c)
target_include_directories(asil_example_c PUBLIC include)
target_compile_options(asil_example_c PRIVATE ${SAFETY_FLAGS})

# ── Test target ──
add_executable(asil_example_c_tests tests/test_project.c)
target_link_libraries(asil_example_c_tests PRIVATE asil_example_c)
target_compile_options(asil_example_c_tests PRIVATE ${SAFETY_FLAGS})

# ── Test runner ──
enable_testing()
add_test(NAME asil_example_c_unit_tests COMMAND asil_example_c_tests)

# ── Coverage target ──
add_custom_target(coverage
    COMMAND ${CMAKE_COMMAND} -E echo "Coverage requires: cmake -DCMAKE_BUILD_TYPE=Coverage .. && make && ctest && gcovr"
)
