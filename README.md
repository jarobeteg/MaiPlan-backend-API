# MaiPlan Backend Design Document 👹

| Author           | Date Created     | Last Edited      | Version | Reviewed By |
|:----------------:|:----------------:|:----------------:|:-------:|:-----------:|
| jarobeteg (Jaro) | November 6, 2025 | November 9, 2025 | 0.1     |-------------|

## Overview 📋
The purpose of this document is to explain the objectives of the project, provide a detailed overview of its technical challanges and their solutions. Furthermore to provide insight into future plans and upcoming implementations. This project represents both a personal learning journey and the realization of my girlfriend's dream project. It is an exploration of different areas within software engineering, where I experiment, overengineer, and get lost in various concepts purely for the sake of learning. Additionally, any ideas or suggestions she brings forward, as well as changes she envisions, are considered an integral part of the project's scope and ongoing development.

## What is the MaiPlan project? 📱
MaiPlan is an Android application to serve as an all in one personal organizer. Combining a daily planner, finance tracker, file manager, note taking tool (with extended list functionality), reminder system, event scheduler, and health tracker. These are the core features planned for the project. The scope will likely expand over time. Future ideas include a shared calendar, a dream wall, a book section (for personal research), and widgets.

## The Backend 💻
The app has a backend server responsible for storing and synchronizing app data. It is built using Python's FastAPI framework, which handles API communication between the app and the server, running on Uvicorn as the web server. PostgreSQL serves as the primary database for data management. The backend is hosted on a Raspberry Pi, with secure connection establish through Tailscalse for remote access.

## Pending ideas 💡
I also have several additional ideas for the backend, and sure they might seem unecessary, but they are purely for learning purposes. These include developing a custom Python API framework written in C++, building my own web server in C to handle API communications, and creating a monitoring program for both the server and the Raspberry Pi itself.
