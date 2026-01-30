import { useState } from 'react'
import './App.css'
import jsPDF from 'jspdf'

function App() {
  const [url, setUrl] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState(0)

  const handleScrape = async () => {
    if (!url.trim()) {
      alert('Please enter an Instagram URL');
      return;
    }

    console.log('🚀 Fetching data for URL:', url);
    setLoading(true);
    setResult(null);
    setProgress(0);

    // Simulate progress animation
    const progressInterval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 90) return prev; // Stop at 90% until actual completion
        // Faster progress at start, slower near end
        if (prev < 30) return prev + 3; // Quick start
        if (prev < 70) return prev + 1.5; // Steady progress
        return prev + 0.5; // Slow down near end
      });
    }, 200);

    try {
      const response = await fetch("http://localhost:8000/get-post-data", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url }),
      });

      console.log('📡 Response status:', response.status);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log('✅ Data received:', data);

      // Complete progress to 100%
      setProgress(100);

      // Small delay to show 100% before showing results
      setTimeout(() => {
        setResult(data);
        clearInterval(progressInterval);
      }, 300);

    } catch (error) {
      console.error('❌ Error fetching data:', error);
      setResult({ error: `Failed to fetch data: ${error.message}` });
      clearInterval(progressInterval);
      setProgress(0);
    } finally {
      setTimeout(() => {
        setLoading(false);
        setProgress(0);
      }, 500);
    }
  }

  const downloadPDF = () => {
    if (!result || result.error) return;
    const pdf = new jsPDF();
    const pageWidth = pdf.internal.pageSize.getWidth();
    const pageHeight = pdf.internal.pageSize.getHeight();
    const margin = 15;
    const contentWidth = pageWidth - (margin * 2);
    let yPos = 20;

    // Helper to remove emojis, as jsPDF often struggles with them
    const removeEmojis = (text) => {
      if (typeof text !== 'string') return text;
      return text.replace(/[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F1E0}-\u{1F1FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}\u{1F900}-\u{1F9FF}\u{1FA70}-\u{1FAFF}\u{2B50}\u{2B55}\u{2934}\u{2935}\u{2B05}\u{2B06}\u{2B07}\u{2B1B}\u{2B1C}\u{2B50}\u{2B55}\u{3030}\u{303D}\u{3297}\u{3299}\u{1F004}\u{1F0CF}\u{1F170}-\u{1F171}\u{1F17E}-\u{1F17F}\u{1F18E}\u{1F191}-\u{1F19A}\u{1F201}-\u{1F202}\u{1F21A}\u{1F22F}\u{1F232}-\u{1F23A}\u{1F250}-\u{1F251}\u{200D}\u{20E3}\u{FE0F}]/gu, '');
    };

    // Header with background
    pdf.setFillColor(131, 58, 180);
    pdf.rect(0, 0, pageWidth, 40, 'F');

    // Title
    pdf.setFontSize(24);
    pdf.setTextColor(255, 255, 255);
    pdf.text('Instagram Analytics Report', pageWidth / 2, 20, { align: 'center' });

    pdf.setFontSize(10);
    pdf.text(`@${removeEmojis(result.username)}`, pageWidth / 2, 30, { align: 'center' });

    yPos = 50;
    pdf.setFontSize(9);
    pdf.setTextColor(120, 120, 120);
    pdf.text(`Generated: ${new Date().toLocaleString()}`, pageWidth / 2, yPos, { align: 'center' });

    yPos = 65;

    // Helper function to check if new page is needed
    const checkNewPage = (requiredSpace) => {
      if (yPos + requiredSpace > pageHeight - 20) {
        pdf.addPage();
        yPos = 20;
        return true;
      }
      return false;
    };

    // Helper function for section headers
    const addSectionHeader = (title) => {
      checkNewPage(20);
      pdf.setFillColor(240, 240, 245);
      pdf.rect(margin, yPos - 5, contentWidth, 8, 'F');
      pdf.setFontSize(14);
      pdf.setTextColor(131, 58, 180);
      pdf.text(title, margin + 5, yPos);
      yPos += 12;
    };

    // Helper function for key-value pairs
    const addKeyValue = (label, value, maxWidth = 120) => {
      checkNewPage(10);
      pdf.setFontSize(10);
      pdf.setTextColor(80, 80, 80);
      pdf.text(label + ':', margin + 5, yPos);

      pdf.setTextColor(0, 0, 0);
      const valueStr = removeEmojis(String(value || 'N/A'));
      const splitValue = pdf.splitTextToSize(valueStr, maxWidth);
      pdf.text(splitValue, margin + 55, yPos);

      yPos += Math.max(6, splitValue.length * 5);
    };

    // Section 1: Creator Information
    addSectionHeader('Creator Information');

    addKeyValue('Username', '@' + removeEmojis(result.username) + (result.is_verified ? ' (Verified)' : ''));
    addKeyValue('Full Name', removeEmojis(result.full_name));

    // Bio with proper wrapping
    if (result.bio && result.bio !== 'No bio available') {
      checkNewPage(20);
      pdf.setTextColor(80, 80, 80);
      pdf.text('Bio:', margin + 5, yPos);
      yPos += 6;

      pdf.setTextColor(0, 0, 0);
      const bioLines = pdf.splitTextToSize(removeEmojis(result.bio), contentWidth - 10);
      pdf.text(bioLines, margin + 5, yPos);
      yPos += bioLines.length * 5 + 6;
    }

    addKeyValue('Followers', result.followers?.toLocaleString());
    addKeyValue('Following', result.following?.toLocaleString());
    addKeyValue('Total Posts', result.total_posts?.toLocaleString());

    yPos += 10;

    // Section 2: Post Metrics
    addSectionHeader('Post Metrics');

    addKeyValue('Likes', result.likes?.toLocaleString());
    addKeyValue('Comments', result.comments_count?.toLocaleString());

    if (result.video_view_count > 0) {
      addKeyValue('Views', result.video_view_count?.toLocaleString());
    }

    addKeyValue('Media Type', removeEmojis(result.media_type));
    addKeyValue('Published', result.publish_date);

    yPos += 10;

    // Section 3: Hashtags
    if (result.hashtags && result.hashtags.length > 0) {
      addSectionHeader('Hashtags');

      pdf.setFontSize(10);
      pdf.setTextColor(0, 0, 0);
      const hashtagText = removeEmojis(result.hashtags.join('  '));
      const splitHashtags = pdf.splitTextToSize(hashtagText, contentWidth - 10);
      pdf.text(splitHashtags, margin + 5, yPos);
      yPos += splitHashtags.length * 5 + 10;
    }

    // Section 4: Caption
    if (result.caption && result.caption !== 'No caption') {
      addSectionHeader('Caption');

      pdf.setFontSize(9);
      pdf.setTextColor(60, 60, 60);
      const captionLines = pdf.splitTextToSize(removeEmojis(result.caption), contentWidth - 10);

      // Split into chunks if too long
      const maxLinesPerPage = 30;
      for (let i = 0; i < captionLines.length; i += maxLinesPerPage) {
        checkNewPage(20);
        const chunk = captionLines.slice(i, i + maxLinesPerPage);
        pdf.text(chunk, margin + 5, yPos);
        yPos += chunk.length * 4;
      }

      yPos += 10;
    }

    // Footer on all pages
    const pageCount = pdf.internal.getNumberOfPages();
    for (let i = 1; i <= pageCount; i++) {
      pdf.setPage(i);
      pdf.setFontSize(8);
      pdf.setTextColor(150, 150, 150);
      pdf.text(
        `Page ${i} of ${pageCount} | Instagram Scraper Analytics`,
        pageWidth / 2,
        pageHeight - 10,
        { align: 'center' }
      );
    }

    // Save PDF
    pdf.save(`instagram-report-${result.username}-${new Date().getTime()}.pdf`);
  }

  return (
    <div className="App">
      {/* Header */}
      <div className="header">
        <h1 className="gradient-text">Instagram Scraper</h1>
        <p>Extract detailed analytics from any Instagram post or reel</p>
      </div>

      {/* Input Section */}
      <div className="input-section">
        <input
          type="text"
          placeholder="Paste Instagram post URL here..."
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleScrape()}
        />
        <button onClick={handleScrape} disabled={loading}>
          <span>{loading ? '⏳ Loading...' : '🔍 Fetch Data'}</span>
        </button>
      </div>

      {/* Action Buttons */}
      {result && !result.error && (
        <div className="action-buttons">
          <button onClick={downloadPDF}>
            <span>📥 Download Report</span>
          </button>
        </div>
      )}

      {/* Loading State with Progress Bar */}
      {loading && (
        <div className="loading">
          <div className="progress-container">
            <div className="progress-circle">
              <svg className="progress-ring" width="120" height="120">
                <circle
                  className="progress-ring-circle-bg"
                  stroke="rgba(255, 255, 255, 0.1)"
                  strokeWidth="8"
                  fill="transparent"
                  r="52"
                  cx="60"
                  cy="60"
                />
                <circle
                  className="progress-ring-circle"
                  stroke="url(#gradient)"
                  strokeWidth="8"
                  fill="transparent"
                  r="52"
                  cx="60"
                  cy="60"
                  style={{
                    strokeDasharray: `${2 * Math.PI * 52}`,
                    strokeDashoffset: `${2 * Math.PI * 52 * (1 - progress / 100)}`,
                  }}
                />
                <defs>
                  <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#833ab4" />
                    <stop offset="50%" stopColor="#fd1d1d" />
                    <stop offset="100%" stopColor="#fcb045" />
                  </linearGradient>
                </defs>
              </svg>
              <div className="progress-text">
                <span className="progress-percentage">{Math.round(progress)}%</span>
              </div>
            </div>
            <p className="progress-message">
              {progress < 30 && '🔍 Connecting to Instagram...'}
              {progress >= 30 && progress < 60 && '📡 Fetching post data...'}
              {progress >= 60 && progress < 90 && '📊 Analyzing metrics...'}
              {progress >= 90 && progress < 100 && '✨ Almost done...'}
              {progress === 100 && '✅ Complete!'}
            </p>
          </div>
        </div>
      )}

      {/* Error State */}
      {result && result.error && (
        <div className="error">
          <h3>❌ Error</h3>
          <p>{result.error}</p>
        </div>
      )}

      {/* Results */}
      {result && !result.error && (
        <div className="results-container">
          {/* Media Section */}
          {(result.display_url || result.thumbnail_url) && (
            <div className="thumbnail-section">
              <div className="thumbnail-card glass-card">
                {result.media_type === 'Video/Reel' ? (
                  <video controls src={result.video_url || result.display_url} style={{ width: '100%', maxHeight: '500px' }} />
                ) : (
                  <img src={result.display_url || result.thumbnail_url} alt="Post thumbnail" />
                )}
              </div>
            </div>
          )}

          {/* Three Column Grid */}
          <div className="metrics-grid">
            {/* Column 1: Full Metrics */}
            <div className="metric-card">
              <h3>📊 Full Metrics</h3>

              {result.profile_pic_url && (
                <img
                  src={result.profile_pic_url}
                  alt="Profile"
                  className="profile-pic-inner"
                  style={{ width: '80px', height: '80px', borderRadius: '50%', margin: '0 auto 20px', display: 'block' }}
                />
              )}

              <div className="metric-item">
                <span className="metric-label">Username</span>
                <span className="metric-value verified">
                  @{result.username}
                  {result.is_verified && <span>✓</span>}
                </span>
              </div>

              <div className="metric-item">
                <span className="metric-label">Full Name</span>
                <span className="metric-value">{result.full_name}</span>
              </div>

              <div className="metric-item">
                <span className="metric-label">Followers</span>
                <span className="metric-value">{result.followers?.toLocaleString()}</span>
              </div>

              <div className="metric-item">
                <span className="metric-label">Following</span>
                <span className="metric-value">{result.following?.toLocaleString()}</span>
              </div>

              <div className="metric-item">
                <span className="metric-label">Total Posts</span>
                <span className="metric-value">{result.total_posts?.toLocaleString()}</span>
              </div>

              <div className="metric-item">
                <span className="metric-label">Post Likes</span>
                <span className="metric-value">{result.likes?.toLocaleString()}</span>
              </div>

              <div className="metric-item">
                <span className="metric-label">Post Comments</span>
                <span className="metric-value">{result.comments_count?.toLocaleString()}</span>
              </div>

              <div className="metric-item">
                <span className="metric-label">Media Type</span>
                <span className="metric-value">{result.media_type}</span>
              </div>
            </div>

            {/* Column 2: Post Metrics */}
            <div className="metric-card">
              <h3>📸 Post Metrics</h3>

              <div className="metric-item">
                <span className="metric-label">Likes</span>
                <span className="metric-value">{result.likes?.toLocaleString()}</span>
              </div>

              <div className="metric-item">
                <span className="metric-label">Comments</span>
                <span className="metric-value">{result.comments_count?.toLocaleString()}</span>
              </div>

              {result.video_view_count > 0 && (
                <div className="metric-item">
                  <span className="metric-label">Views</span>
                  <span className="metric-value">{result.video_view_count?.toLocaleString()}</span>
                </div>
              )}

              <div className="metric-item">
                <span className="metric-label">Publish Date</span>
                <span className="metric-value">{result.publish_date}</span>
              </div>

              <div className="metric-item">
                <span className="metric-label">Location</span>
                <span className="metric-value">{result.location || 'N/A'}</span>
              </div>

              <div className="metric-item">
                <span className="metric-label">Media Type</span>
                <span className="metric-value">{result.media_type}</span>
              </div>

              {result.hashtags && result.hashtags.length > 0 && (
                <div className="metric-item">
                  <span className="metric-label">Hashtags</span>
                  <div className="hashtags">
                    {result.hashtags.map((tag, idx) => (
                      <span key={idx} className="hashtag">{tag}</span>
                    ))}
                  </div>
                </div>
              )}

              <div className="metric-item" style={{ flexDirection: 'column', alignItems: 'flex-start' }}>
                <span className="metric-label" style={{ marginBottom: '8px' }}>Caption</span>
                <div className="caption-text">{result.caption}</div>
              </div>
            </div>

            {/* Column 3: Creator Metrics */}
            <div className="metric-card">
              <h3>Creator Metrics</h3>

              <div className="metric-item">
                <span className="metric-label">Username</span>
                <span className="metric-value verified">
                  @{result.username}
                  {result.is_verified && <span>✓</span>}
                </span>
              </div>

              <div className="metric-item">
                <span className="metric-label">Full Name</span>
                <span className="metric-value">{result.full_name}</span>
              </div>

              <div className="metric-item" style={{ flexDirection: 'column', alignItems: 'flex-start' }}>
                <span className="metric-label" style={{ marginBottom: '8px' }}>Bio</span>
                <div className="caption-text">{result.bio}</div>
              </div>

              <div className="metric-item">
                <span className="metric-label">Followers</span>
                <span className="metric-value">{result.followers?.toLocaleString()}</span>
              </div>

              <div className="metric-item">
                <span className="metric-label">Following</span>
                <span className="metric-value">{result.following?.toLocaleString()}</span>
              </div>

              <div className="metric-item">
                <span className="metric-label">Total Posts</span>
                <span className="metric-value">{result.total_posts?.toLocaleString()}</span>
              </div>

              <div className="metric-item">
                <span className="metric-label">Date Joined</span>
                <span className="metric-value">{result.date_joined || 'N/A'}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default App