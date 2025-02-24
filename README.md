# MeowAI

MeowAI is an AI-driven consulting application designed to facilitate structured consulting calls. The application leverages advanced technologies to manage calls, transcribe conversations, and provide a seamless experience for both consultants and clients.

## Table of Contents

- [Features](#features)
- [Technologies Used](#technologies-used)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [Contributing](#contributing)
- [License](#license)

## Features

- **AI-Powered Conversations**: Utilizes AI models to conduct structured consulting calls.
- **Real-Time Transcription**: Automatically transcribes conversations for record-keeping and analysis.
- **WebSocket Support**: Enables real-time communication between clients and the server.
- **Call Management**: Initiates, manages, and terminates calls with appropriate protocols.
- **CORS Support**: Configured to allow cross-origin requests for web applications.

## Technologies Used

- **Backend Framework**: [Quart](https://pgjones.gitlab.io/quart/)
- **Database**: [MongoDB](https://www.mongodb.com/)
- **WebSocket Library**: [websockets](https://websockets.readthedocs.io/en/stable/)
- **API Client**: [Plivo](https://www.plivo.com/)
- **AI Model**: [Deepgram](https://deepgram.com/)
- **Data Validation**: [Pydantic](https://pydantic-docs.helpmanual.io/)
- **Environment Management**: [python-dotenv](https://pypi.org/project/python-dotenv/)

## Installation

To set up the project locally, follow these steps:

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/meowai.git
   cd meowai
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up your configuration file:
   - Create a `config.json` file in the root directory with the following structure:
     ```json
     {
       "mongodb": {
         "url": "your_mongodb_connection_string",
         "dbName": "your_database_name"
       },
       "PLIVO_NUMBER": "your_plivo_number",
       "PLIVO_AUTH_ID": "your_plivo_auth_id",
       "PLIVO_AUTH_TOKEN": "your_plivo_auth_token",
       "DEEPGRAM_API_KEY": "your_deepgram_api_key",
       "server": {
         "port": 5000
       }
     }
     ```

## Usage

To run the application, execute the following command:

The application will start on the specified port (default is 5000). You can access the health check endpoint at `http://localhost:5000/`.

## API Endpoints

### Health Check

- **GET** `/`
  - Returns the status of the application, including connection statuses for MongoDB, Plivo, and Deepgram.

### Make a Call

- **POST** `/make-a-call`
  - Initiates an outbound call.
  - **Request Body**:
    ```json
    {
      "target_id": "string"
    }
    ```

### Webhook

- **GET/POST** `/webhook/<call_id>`
  - Handles incoming webhook requests from Plivo.

### Media Stream

- **WebSocket** `/media-stream/<call_id>`
  - Manages the media stream for the call.

## Contributing

Contributions are welcome! Please follow these steps to contribute:

1. Fork the repository.
2. Create a new branch (`git checkout -b feature/YourFeature`).
3. Make your changes and commit them (`git commit -m 'Add some feature'`).
4. Push to the branch (`git push origin feature/YourFeature`).
5. Open a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.