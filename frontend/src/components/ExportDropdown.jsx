import { useState } from 'react';
import { downloadExport } from '../api/exportApi';
import './ExportDropdown.css';

export default function ExportDropdown({ versionId }) {
    const [format, setFormat] = useState('txt');
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState({ text: '', type: '' });

    const handleExport = async () => {
        if (!versionId) return;

        setLoading(true);
        setMessage({ text: '', type: '' });

        try {
            await downloadExport(versionId, format);
            setMessage({ text: 'Export successful!', type: 'success' });
            
            // clear success message after 3 seconds
            setTimeout(() => {
                setMessage({ text: '', type: '' });
            }, 3000);
        } catch (err) {
            setMessage({ text: `Failed to export: ${err.message}`, type: 'error' });
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="export-container">
            <label htmlFor="export-format" className="sr-only">Format</label>
            <select 
                id="export-format"
                value={format} 
                onChange={(e) => setFormat(e.target.value)}
                disabled={!versionId || loading}
            >
                <option value="txt">.txt (Plain Text)</option>
                <option value="md">.md (Markdown)</option>
                <option value="json">.json (JSON)</option>
            </select>
            
            <button 
                onClick={handleExport} 
                disabled={!versionId || loading}
                className="export-btn"
            >
                {loading ? 'Exporting...' : 'Export'}
            </button>
            
            {message.text && (
                <span className={`export-message ${message.type}`}>
                    {message.text}
                </span>
            )}
        </div>
    );
}
