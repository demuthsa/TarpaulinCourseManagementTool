# TarpaulinCourseManagementTool


![Display from admin POV](https://i.imgur.com/lHEPPVJ.png)


Here is a summary of all the API endpoints I created [here](docs/assignment6-api-doc.pdf)


## Project Summary
The project involved implementing a complete RESTful API for Tarpaulin, a lightweight course management tool serving as an alternative to Canvas. The API was developed using Python 3 and is deployed on Google Cloud Platform using Google App Engine and Datastore. Authentication is managed using Auth0.

## Key Features
- **User Management**: Users can log in, and their roles (admin, instructor, student) will determine access levels.
- **Course Management**: Admins can create, update, and delete courses. Courses can be accessed and enrolled in by users.
- **File Handling**: Users can upload, view, and delete avatars stored in Google Cloud Storage.
- **Authorization**: Most endpoints are protected and require JWT authentication.

## Technologies Used
- **Google Cloud Platform (GCP)**: Deployment on Google App Engine, data storage in Datastore.
- **Auth0**: Authentication and JWT management.
- **Python 3**: Backend development.
- **Google Cloud Storage**: Handling user avatar files.

## Endpoints Overview
- **User Login**: `POST /users/login` - Auth0 issues JWTs.
- **Get All Users**: `GET /users` - Admin-only access.
- **Get User Details**: `GET /users/:id` - Admin or user-specific access.
- **Manage User Avatar**: `POST /users/:id/avatar`, `GET /users/:id/avatar`, `DELETE /users/:id/avatar` - User-specific access.
- **Course Management**: CRUD operations on courses by Admins, with some endpoints accessible to all users or course instructors.

## Data Management
- **Users**: Pre-created in Auth0, roles stored in Datastore.
- **Courses and Enrollment**: Designed and managed within Datastore.
