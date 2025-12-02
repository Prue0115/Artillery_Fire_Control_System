cmake_minimum_required(VERSION 3.16)
project(AFCSQt LANGUAGES CXX)

set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC OFF)

find_package(QT NAMES Qt6 Qt5 REQUIRED COMPONENTS Widgets)
find_package(Qt${QT_VERSION_MAJOR} REQUIRED COMPONENTS Widgets)

set(PROJECT_SOURCES
    src/main.cpp
    src/MainWindow.cpp
    src/MainWindow.h
    src/RangeTable.cpp
    src/RangeTable.h
)

set(UI_FILES src/MainWindow.ui)

if(${QT_VERSION_MAJOR} GREATER_EQUAL 6)
    qt_add_executable(AFCSQt
        MANUAL_FINALIZATION
        ${PROJECT_SOURCES}
    )

    qt_add_ui_files(AFCSQt ${UI_FILES})
else()
    qt5_wrap_ui(UIC_FILES ${UI_FILES})

    add_executable(AFCSQt
        ${PROJECT_SOURCES}
        ${UIC_FILES}
    )
endif()

target_compile_features(AFCSQt PRIVATE cxx_std_17)
target_include_directories(AFCSQt PRIVATE
    src
    ${CMAKE_CURRENT_BINARY_DIR}
)
target_link_libraries(AFCSQt PRIVATE Qt${QT_VERSION_MAJOR}::Widgets)

if(${QT_VERSION_MAJOR} GREATER_EQUAL 6)
    qt_finalize_executable(AFCSQt)
endif()

install(TARGETS AFCSQt)
