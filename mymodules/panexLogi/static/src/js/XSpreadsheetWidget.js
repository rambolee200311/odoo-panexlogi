const { Component, useState, onMounted, useEffect } = owl;

class XSpreadsheetWidget extends Component {
    setup() {
        // Initialize state with parsed JSON data or an empty object
        this.state = useState({
            data: this._parseJSON(this.props.value),
        });

        // Initialize the spreadsheet when the component is mounted
        onMounted(() => this._initializeSpreadsheet());

        // Update the spreadsheet when props.value changes
        useEffect(
            () => {
                if (this.spreadsheet) {
                    const newData = this._parseJSON(this.props.value);
                    this.spreadsheet.loadData(newData);
                    this.state.data = newData;
                }
            },
            () => [this.props.value]
        );
    }

    /**
     * Parse JSON data with error handling.
     * @param {string} value - The JSON string to parse.
     * @returns {Object} - Parsed JSON object or an empty object if parsing fails.
     */
    _parseJSON(value) {
        try {
            return value ? JSON.parse(value) : {};
        } catch (error) {
            console.error("Failed to parse JSON:", error);
            return {};
        }
    }

    /**
     * Initialize the x_spreadsheet instance.
     */
    _initializeSpreadsheet() {
        try {
            // Clear the container
            this.el.innerHTML = '';

            // Initialize the spreadsheet
            this.spreadsheet = new window.x_spreadsheet(this.el, {
                mode: 'edit', // Allow editing
                showToolbar: true, // Show the toolbar
                showGrid: true, // Show the grid
            });

            // Load initial data
            this.spreadsheet.loadData(this.state.data);

            // Handle changes in the spreadsheet
            this.spreadsheet.change((data) => {
                this.state.data = data;
                this.props.update(JSON.stringify(data));
            });
        } catch (error) {
            console.error("Failed to initialize spreadsheet:", error);
        }
    }
}

// Define the template for the widget
XSpreadsheetWidget.template = 'panexLogi.XSpreadsheetWidget';

// Register the widget
owl.Component.env = owl.Component.env || {};
owl.Component.env.components = owl.Component.env.components || {};
owl.Component.env.components.XSpreadsheetWidget = XSpreadsheetWidget;