const API_BASE = "https://promptbox-9d83.onrender.com";


/**
 * Download a prompt version export as a file. Triggers a browser download
 * by creating a temporary anchor element with the response blob.
 * @param {string} token - JWT authentication token
 * @param {number} versionId - The version ID to export
 * @param {string} format - Export format ("txt" | "md" | "json")
 * @returns {Promise<void>} Resolves after the download is triggered
 * @throws {Error} Server error detail message on non-OK responses
 */
export async function downloadExport(token, versionId, format) {
    const res = await fetch(`${API_BASE}/api/export/${versionId}?format=${format}`, {
        method: "GET",
        headers: {
            Authorization: `Bearer ${token}`
        }
    });

    if (!res.ok) {
        let errorMessage = "Failed to export version";
        try {
            const errorData = await res.json();
            if (errorData.detail) {
                errorMessage = errorData.detail;
            }
        } catch (e) {
            // response was not JSON, ignore
        }
        throw new Error(errorMessage);
    }

    // Get the filename from the Content-Disposition header if possible
    let filename = `export-${versionId}.${format}`;
    const disposition = res.headers.get('Content-Disposition');
    if (disposition && disposition.includes('filename=')) {
        const matches = /filename="([^"]+)"/.exec(disposition);
        if (matches != null && matches[1]) filename = matches[1];
    }

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    
    // Create a temporary link element to trigger the download
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    
    // Cleanup
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
}
