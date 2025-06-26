import React, { useState } from 'react';
import toast from 'react-hot-toast';

function Analytics() {
  const [text, setText] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('sentiment');

  const analyzeSentiment = async () => {
    if (!text.trim()) {
      toast.error('Please enter some text to analyze');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch('/ml/sentiment', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: text.trim(), language: 'en' }),
      });

      if (response.ok) {
        const data = await response.json();
        setResult(data.data);
        toast.success('Sentiment analysis completed!');
      } else {
        throw new Error('Analysis failed');
      }
    } catch (error) {
      console.error('Error:', error);
      toast.error('Failed to analyze sentiment');
    } finally {
      setLoading(false);
    }
  };

  const extractEntities = async () => {
    if (!text.trim()) {
      toast.error('Please enter some text to analyze');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch('/ml/extract-entities', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: text.trim(), language: 'en' }),
      });

      if (response.ok) {
        const data = await response.json();
        setResult(data.data);
        toast.success('Entity extraction completed!');
      } else {
        throw new Error('Extraction failed');
      }
    } catch (error) {
      console.error('Error:', error);
      toast.error('Failed to extract entities');
    } finally {
      setLoading(false);
    }
  };

  const getSentimentColor = (sentiment) => {
    switch (sentiment) {
      case 'positive': return 'text-green-600 bg-green-100';
      case 'negative': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getEntityColor = (label) => {
    const colors = {
      'PERSON': 'bg-blue-100 text-blue-800',
      'ORG': 'bg-green-100 text-green-800',
      'GPE': 'bg-purple-100 text-purple-800',
      'PRODUCT': 'bg-yellow-100 text-yellow-800',
      'EVENT': 'bg-pink-100 text-pink-800',
      'MONEY': 'bg-indigo-100 text-indigo-800',
      'DATE': 'bg-gray-100 text-gray-800',
    };
    return colors[label] || 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="px-4 py-6 sm:px-0">
      <div className="border-4 border-dashed border-gray-200 rounded-lg p-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-8">Text Analytics</h1>
        
        {/* Input Section */}
        <div className="bg-white p-6 rounded-lg shadow mb-8">
          <label htmlFor="text-input" className="block text-sm font-medium text-gray-700 mb-2">
            Enter text to analyze
          </label>
          <textarea
            id="text-input"
            rows={4}
            className="shadow-sm focus:ring-blue-500 focus:border-blue-500 mt-1 block w-full sm:text-sm border border-gray-300 rounded-md p-3"
            placeholder="Type or paste your text here..."
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          
          <div className="mt-4 flex space-x-4">
            <button
              onClick={analyzeSentiment}
              disabled={loading}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
            >
              {loading ? 'Analyzing...' : 'Analyze Sentiment'}
            </button>
            
            <button
              onClick={extractEntities}
              disabled={loading}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50"
            >
              {loading ? 'Extracting...' : 'Extract Entities'}
            </button>
          </div>
        </div>

        {/* Results Section */}
        {result && (
          <div className="bg-white p-6 rounded-lg shadow">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Analysis Results</h2>
            
            {/* Tabs */}
            <div className="border-b border-gray-200 mb-4">
              <nav className="-mb-px flex space-x-8">
                <button
                  onClick={() => setActiveTab('sentiment')}
                  className={`py-2 px-1 border-b-2 font-medium text-sm ${
                    activeTab === 'sentiment'
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  Sentiment
                </button>
                <button
                  onClick={() => setActiveTab('entities')}
                  className={`py-2 px-1 border-b-2 font-medium text-sm ${
                    activeTab === 'entities'
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  Entities
                </button>
                <button
                  onClick={() => setActiveTab('details')}
                  className={`py-2 px-1 border-b-2 font-medium text-sm ${
                    activeTab === 'details'
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  Details
                </button>
              </nav>
            </div>

            {/* Sentiment Tab */}
            {activeTab === 'sentiment' && result.sentiment && (
              <div>
                <div className="mb-4">
                  <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getSentimentColor(result.sentiment)}`}>
                    {result.sentiment.charAt(0).toUpperCase() + result.sentiment.slice(1)}
                  </span>
                  <span className="ml-2 text-sm text-gray-500">
                    Confidence: {(result.confidence * 100).toFixed(1)}%
                  </span>
                </div>
                
                {result.scores && (
                  <div className="space-y-2">
                    <h3 className="text-sm font-medium text-gray-700">Detailed Scores:</h3>
                    {Object.entries(result.scores).map(([sentiment, score]) => (
                      <div key={sentiment} className="flex items-center">
                        <span className="w-20 text-sm text-gray-600 capitalize">{sentiment}:</span>
                        <div className="flex-1 bg-gray-200 rounded-full h-2 ml-2">
                          <div
                            className={`h-2 rounded-full ${
                              sentiment === 'positive' ? 'bg-green-500' :
                              sentiment === 'negative' ? 'bg-red-500' : 'bg-gray-500'
                            }`}
                            style={{ width: `${score * 100}%` }}
                          ></div>
                        </div>
                        <span className="ml-2 text-sm text-gray-600">{(score * 100).toFixed(1)}%</span>
                      </div>
                    ))}
                  </div>
                )}

                {result.emotions && Object.keys(result.emotions).length > 0 && (
                  <div className="mt-6">
                    <h3 className="text-sm font-medium text-gray-700 mb-2">Emotions:</h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                      {Object.entries(result.emotions)
                        .sort(([,a], [,b]) => b - a)
                        .slice(0, 8)
                        .map(([emotion, score]) => (
                        <div key={emotion} className="bg-gray-50 p-2 rounded text-center">
                          <div className="text-sm font-medium text-gray-900 capitalize">{emotion}</div>
                          <div className="text-xs text-gray-500">{(score * 100).toFixed(1)}%</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Entities Tab */}
            {activeTab === 'entities' && result.entities && (
              <div>
                <div className="mb-4">
                  <span className="text-sm text-gray-500">
                    Found {result.entities.length} entities
                  </span>
                </div>
                
                <div className="space-y-2">
                  {result.entities.map((entity, index) => (
                    <div key={index} className="flex items-center space-x-2">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getEntityColor(entity.label)}`}>
                        {entity.label}
                      </span>
                      <span className="text-sm font-medium text-gray-900">{entity.text}</span>
                      {entity.description && (
                        <span className="text-sm text-gray-500">({entity.description})</span>
                      )}
                    </div>
                  ))}
                </div>

                {result.hashtags && result.hashtags.length > 0 && (
                  <div className="mt-6">
                    <h3 className="text-sm font-medium text-gray-700 mb-2">Hashtags:</h3>
                    <div className="flex flex-wrap gap-2">
                      {result.hashtags.map((hashtag, index) => (
                        <span key={index} className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                          #{hashtag}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {result.mentions && result.mentions.length > 0 && (
                  <div className="mt-4">
                    <h3 className="text-sm font-medium text-gray-700 mb-2">Mentions:</h3>
                    <div className="flex flex-wrap gap-2">
                      {result.mentions.map((mention, index) => (
                        <span key={index} className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                          @{mention}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Details Tab */}
            {activeTab === 'details' && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-gray-50 p-3 rounded">
                    <div className="text-sm font-medium text-gray-500">Processing Time</div>
                    <div className="text-lg font-semibold text-gray-900">
                      {result.processing_time_ms?.toFixed(1) || 0}ms
                    </div>
                  </div>
                  <div className="bg-gray-50 p-3 rounded">
                    <div className="text-sm font-medium text-gray-500">Text Length</div>
                    <div className="text-lg font-semibold text-gray-900">
                      {result.text_length || 0} chars
                    </div>
                  </div>
                  <div className="bg-gray-50 p-3 rounded">
                    <div className="text-sm font-medium text-gray-500">Language</div>
                    <div className="text-lg font-semibold text-gray-900">
                      {result.language_detected || 'N/A'}
                    </div>
                  </div>
                  <div className="bg-gray-50 p-3 rounded">
                    <div className="text-sm font-medium text-gray-500">Entity Count</div>
                    <div className="text-lg font-semibold text-gray-900">
                      {result.entity_count || result.entities?.length || 0}
                    </div>
                  </div>
                </div>

                {result.tokens && (
                  <div>
                    <h3 className="text-sm font-medium text-gray-700 mb-2">Tokens:</h3>
                    <div className="bg-gray-50 p-3 rounded text-sm text-gray-600">
                      {result.tokens.slice(0, 20).join(', ')}
                      {result.tokens.length > 20 && '...'}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default Analytics;