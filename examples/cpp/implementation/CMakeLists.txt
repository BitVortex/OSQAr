cmake_minimum_required(VERSION 3.16)
project(osqar_tsim_cpp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

option(OSQAR_COVERAGE "Enable code coverage instrumentation" OFF)

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

if(OSQAR_COVERAGE)
    if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
        foreach(tgt tsim junit_tests)
            target_compile_options(${tgt} PRIVATE -O0 -g --coverage)
            if(COMMAND target_link_options)
                target_link_options(${tgt} PRIVATE --coverage)
            else()
                target_link_libraries(${tgt} PRIVATE --coverage)
            endif()
        endforeach()
    endif()
endif()
