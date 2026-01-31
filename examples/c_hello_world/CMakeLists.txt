cmake_minimum_required(VERSION 3.16)
project(osqar_tsim_c LANGUAGES C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

add_library(tsim
    src/tsim.c
)

target_include_directories(tsim PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

add_executable(junit_tests
    tests/test_tsim.c
)

target_link_libraries(junit_tests PRIVATE tsim)
