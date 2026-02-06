cmake_minimum_required(VERSION 3.16)
project(osqar_project_cpp CXX)

add_library(osqar_project STATIC src/project.cpp)
target_include_directories(osqar_project PUBLIC include)

add_executable(osqar_project_tests tests/test_project.cpp)
target_link_libraries(osqar_project_tests PRIVATE osqar_project)
