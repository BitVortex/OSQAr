cmake_minimum_required(VERSION 3.16)
project(osqar_tsim_cpp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_library(tsim
    src/tsim.cpp
)

target_include_directories(tsim PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

add_executable(junit_tests
    tests/test_tsim.cpp
)

target_link_libraries(junit_tests PRIVATE tsim)
