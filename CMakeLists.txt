cmake_minimum_required(VERSION 3.16)
project(AFCSQt LANGUAGES CXX)

set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC ON)

find_package(QT NAMES Qt6 Qt5 REQUIRED COMPONENTS Widgets)
find_package(Qt${QT_VERSION_MAJOR} REQUIRED COMPONENTS Widgets)

set(PROJECT_SOURCES
    src/main.cpp
    src/MainWindow.cpp
    src/MainWindow.h
    src/MainWindow.ui
    src/RangeTable.cpp
    src/RangeTable.h
)

add_executable(AFCSQt ${PROJECT_SOURCES})

target_compile_features(AFCSQt PRIVATE cxx_std_17)
target_include_directories(AFCSQt PRIVATE src)
target_link_libraries(AFCSQt PRIVATE Qt${QT_VERSION_MAJOR}::Widgets)

install(TARGETS AFCSQt)
