
import React, { useEffect, useState } from "react";

const API_BASE_URL = "http://localhost:8000/api";
const emptyFormData = {
    name: "",
    dob: "",
    gender: "",
    address: "",
    pincode: ""
};

async function requestApi(url, options) {
    const response = await fetch(url, options);
    const result = response.status === 204 ? null : await response.json();

    if (!response.ok) {
        const validationDetails = Object.entries(result?.details || {})
            .map(([field, messages]) => `${field}: ${[].concat(messages).join(", ")}`)
            .join("; ");
        const message = result?.error || result?.detail || "Request failed.";
        throw new Error(
            validationDetails ? `${message} (${validationDetails})` : message
        );
    }

    return result;
}

function MainPage() {
    const [file, setFile] = useState(null);
    const [formData, setFormData] = useState(emptyFormData);
    const [records, setRecords] = useState([]);
    const [editingId, setEditingId] = useState(null);
    const [error, setError] = useState("");
    const [uploading, setUploading] = useState(false);
    const [saving, setSaving] = useState(false);

    const loadRecords = async () => {
        try {
            const data = await requestApi(`${API_BASE_URL}/aadhaar/`);
            setRecords(data);
        } catch (requestError) {
            setError(`Could not load saved records: ${requestError.message}`);
        }
    };

    useEffect(() => {
        loadRecords();
    }, []);

    const handleFileChange = async (e) => {
        const selectedFile = e.target.files[0];
        if (!selectedFile) return;

        const allowedTypes = ["image/jpeg", "image/png", "application/pdf"];
        if (!allowedTypes.includes(selectedFile.type)) {
            setError("Please upload a JPG, PNG or PDF file.");
            e.target.value = "";
            return;
        }

        setFile(selectedFile);
        setError("");
        setUploading(true);

        const uploadData = new FormData();
        uploadData.append("file", selectedFile);

        try {
            const result = await requestApi(`${API_BASE_URL}/aadhaar-ocr/`, {
                method: "POST",
                body: uploadData
            });
            setFormData({ ...emptyFormData, ...result.data });
        } catch (requestError) {
            setError(`Could not read the uploaded document: ${requestError.message}`);
        } finally {
            setUploading(false);
        }
    };

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData((currentData) => ({ ...currentData, [name]: value }));
    };

    const resetForm = () => {
        setFormData(emptyFormData);
        setEditingId(null);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError("");
        setSaving(true);

        try {
            const isEditing = editingId !== null;
            await requestApi(
                isEditing
                    ? `${API_BASE_URL}/aadhaar/${editingId}/`
                    : `${API_BASE_URL}/save-aadhaar/`,
                {
                    method: isEditing ? "PATCH" : "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(formData)
                }
            );
            resetForm();
            await loadRecords();
        } catch (requestError) {
            setError(`Could not save the details: ${requestError.message}`);
        } finally {
            setSaving(false);
        }
    };

    const handleEdit = (record) => {
        setFormData({
            name: record.name,
            dob: record.dob,
            gender: record.gender,
            address: record.address,
            pincode: record.pincode
        });
        setEditingId(record.id);
        setError("");
        window.scrollTo({ top: 0, behavior: "smooth" });
    };

    const handleDelete = async (id) => {
        if (!window.confirm("Delete this record?")) return;

        setError("");
        try {
            await requestApi(`${API_BASE_URL}/aadhaar/${id}/`, {
                method: "DELETE"
            });
            if (editingId === id) resetForm();
            await loadRecords();
        } catch (requestError) {
            setError(`Could not delete the record: ${requestError.message}`);
        }
    };


    return (

        <div style={styles.container}>

            <h2>Aadhaar Card OCR</h2>

            <p>
                Upload your Aadhaar card to extract your details.
            </p>

            {error && <p role="alert" style={styles.error}>{error}</p>}

            <div style={styles.uploadBox}>

                <h3>Upload Aadhaar Document</h3>

                <input
                    type="file"
                    accept=".jpg,.jpeg,.png,.pdf"
                    onChange={handleFileChange}
                />

                {file && <p>Selected File: {file.name}</p>}
                {uploading && <p>Reading document...</p>}

            </div>

            <form onSubmit={handleSubmit}>

                <h3>Personal Information</h3>

                <label>Name</label>
                <input type="text" name="name" value={formData.name} onChange={handleChange} placeholder="Enter your name"/>

                <label>Date of Birth</label>
                <input type="date" name="dob" value={formData.dob} onChange={handleChange}/>
                
                <label>Gender</label>
                <select
                    name="gender"
                    value={formData.gender}
                    onChange={handleChange}
                    
                >
                    <option value="">Select Gender</option>
                    <option value="Male">Male</option>
                    <option value="Female">Female</option>
                    <option value="Other">Other</option>
                </select>

                <label>Address</label>

                <textarea
                    name="address"
                    value={formData.address}
                    onChange={handleChange}
                    placeholder="Enter your address"
                    
                />

                <label>PIN Code</label>

                <input type="text" name="pincode" value={formData.pincode} onChange={handleChange} placeholder="Enter PIN Code" maxLength="6" />

                <button type="submit" disabled={saving || uploading}>
                    {saving ? "Saving..." : editingId !== null ? "Update" : "Submit"}
                </button>
                {editingId !== null && (
                    <button type="button" onClick={resetForm}>
                        Cancel
                    </button>
                )}

            </form>

            <section style={styles.recordsSection}>
                <h3>Saved Aadhaar Details</h3>
                {records.length === 0 ? (
                    <p>No saved records.</p>
                ) : (
                    <div style={styles.tableWrapper}>
                        <table style={styles.table}>
                            <thead>
                                <tr>
                                    <th style={styles.cell}>Name</th>
                                    <th style={styles.cell}>Date of Birth</th>
                                    <th style={styles.cell}>Gender</th>
                                    <th style={styles.cell}>Address</th>
                                    <th style={styles.cell}>PIN Code</th>
                                    <th style={styles.cell}>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {records.map((record) => (
                                    <tr key={record.id}>
                                        <td style={styles.cell}>{record.name}</td>
                                        <td style={styles.cell}>{record.dob}</td>
                                        <td style={styles.cell}>{record.gender}</td>
                                        <td style={styles.cell}>{record.address}</td>
                                        <td style={styles.cell}>{record.pincode}</td>
                                        <td style={styles.cell}>
                                            <button type="button" onClick={() => handleEdit(record)}>
                                                Edit
                                            </button>{" "}
                                            <button type="button" onClick={() => handleDelete(record.id)}>
                                                Delete
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </section>

        </div>

    );

}


// Basic CSS styling
const styles = {

    container: {
        maxWidth: "1000px",
        margin: "40px auto",
        padding: "25px",
        backgroundColor: "#ffffff",
        borderRadius: "10px",
        boxShadow: "0px 0px 10px #cccccc",
        fontFamily: "Arial"
    },

    uploadBox: {
        padding: "20px",
        marginBottom: "20px",
        border: "1px dashed gray",
        borderRadius: "8px"
    },
    recordsSection: {
        marginTop: "32px"
    },
    tableWrapper: {
        overflowX: "auto"
    },
    table: {
        width: "100%",
        borderCollapse: "collapse",
        textAlign: "left"
    },
    cell: {
        padding: "10px",
        border: "1px solid #cccccc",
        verticalAlign: "top"
    },
    error: {
        color: "#b00020"
    }

};

export default MainPage;
