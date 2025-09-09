# Idealista Scraper WordPress Plugin

This WordPress plugin provides a user interface for the Idealista Scraper backend. It allows you to start and stop scraping sessions, monitor their status, and view the scraped data from within your WordPress admin dashboard.

## Requirements

*   A running instance of the Idealista Scraper backend.
*   WordPress version 5.0 or higher.
*   PHP version 7.2 or higher.

## Installation

### Backend Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

2.  **Install Python dependencies:**
    Navigate to the `backend` directory and install the required Python packages using pip.
    ```bash
    cd backend
    pip install -r requirements.txt
    ```

3.  **Configure the environment:**
    Create a `.env` file in the `backend` directory by copying the `.env.example` file.
    ```bash
    cp .env.example .env
    ```
    Edit the `.env` file and provide the necessary configuration, such as your MongoDB connection string.

4.  **Run the backend server:**
    From the `backend` directory, run the following command to start the FastAPI server:
    ```bash
    uvicorn server:app --host 0.0.0.0 --port 8000
    ```
    The server will be running at `http://<your_server_ip>:8000`.

### Plugin Setup

1.  **Build the plugin zip file:**
    From the root of the project directory, run the `build.sh` script to create a distributable zip file of the plugin.
    ```bash
    ./build.sh
    ```
    This will create a file named `wp-idealista-scraper.<version>.zip` in the `build` directory.

2.  **Install the plugin in WordPress:**
    -   Log in to your WordPress admin dashboard.
    -   Navigate to **Plugins > Add New**.
    -   Click the **Upload Plugin** button.
    -   Choose the `wp-idealista-scraper.<version>.zip` file you created and click **Install Now**.
    -   Activate the plugin.

3.  **Configure the plugin:**
    -   Navigate to the **Idealista Scraper** menu in your WordPress admin dashboard.
    -   In the **API Settings** section, enter the URL of your running backend server (e.g., `http://<your_server_ip>:8000`).
    -   Click **Save Changes**.

## Usage

Once the plugin is installed and configured, you can use the Idealista Scraper dashboard to:

*   **Start a new scraping session:** Click the "Start New Scraping Session" button to begin scraping.
*   **Monitor session status:** The dashboard will automatically update to show the status of all scraping sessions.
*   **Solve CAPTCHAs:** If a session requires a CAPTCHA to be solved, a CAPTCHA image and input field will appear. Enter the solution to continue scraping.
*   **View scraped data:** The "Scraped Data" section will display the properties that have been scraped from Idealista.

## Development

The plugin is structured using a boilerplate that separates the admin-facing functionality, internationalization, and the core plugin logic.

*   `wp-idealista-scraper.php`: The main plugin file.
*   `includes/`: Contains the core plugin classes.
*   `admin/`: Contains the admin-facing functionality.
*   `assets/`: Contains the CSS and JavaScript for the plugin.

To contribute to the development, you can edit the files directly and then run the `build.sh` script to create a new zip file.
