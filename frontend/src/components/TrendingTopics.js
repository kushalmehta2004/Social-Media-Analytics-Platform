import React, { useState, useEffect } from 'react';
import toast from 'react-hot-toast';

function TrendingTopics() {
  const [trending, setTrending] = useState([]);
  const [loading, setLoading] = useState(true);
  const [timeframe, setTimeframe] = useState('24');
  const [platform, setPlatform] = useState('all');

  useEffect(() => {
    fetchTrendingTopics();
  }, [timeframe, platform]);

  const fetchTrendingTopics = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        hours: timeframe,
        limit: '20'
      });
      
      if (platform !== 'all') {
        params.append('platform', platform);
      }

      const response = await fetch(`/analytics/trending?${params}`);
      if (response.ok) {
        const data = await response.json();
        setTrending(data.data.topics || []);
      } else {
        throw new Error('Failed to fetch trending topics');
      }
    } catch (error) {
      console.error('Error:', error);
      toast.error('Failed to load trending topics');
    } finally {
      setLoading(false);
    }
  };

  const getSentimentColor = (score) => {
    if (score > 0.1) return 'text-green-600 bg-green-100';
    if (score < -0.1) return 'text-red-600 bg-red-100';
    return 'text-gray-600 bg-gray-100';
  };

  const getSentimentLabel = (score) => {
    if (score > 0.1) return 'Positive';
    if (score < -0.1) return 'Negative';
    return 'Neutral';
  };

  const getGrowthColor = (rate) => {
    if (rate > 1.5) return 'text-green-600';
    if (rate > 1.0) return 'text-yellow-600';
    return 'text-gray-600';
  };

  return (
    <div className="px-4 py-6 sm:px-0">
      <div className="border-4 border-dashed border-gray-200 rounded-lg p-6">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Trending Topics</h1>
          
          {/* Filters */}
          <div className="flex space-x-4">
            <select
              value={timeframe}
              onChange={(e) => setTimeframe(e.target.value)}
              className="block w-32 pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md"
            >
              <option value="1">Last Hour</option>
              <option value="6">Last 6 Hours</option>
              <option value="24">Last 24 Hours</option>
              <option value="168">Last Week</option>
            </select>
            
            <select
              value={platform}
              onChange={(e) => setPlatform(e.target.value)}
              className="block w-32 pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md"
            >
              <option value="all">All Platforms</option>
              <option value="twitter">Twitter</option>
              <option value="reddit">Reddit</option>
              <option value="instagram">Instagram</option>
            </select>
          </div>
        </div>

        {loading ? (
          <div className="flex justify-center items-center h-64">
            <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-500"></div>
          </div>
        ) : trending.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-gray-500 text-lg">No trending topics found</div>
            <div className="text-gray-400 text-sm mt-2">Try adjusting your filters</div>
          </div>
        ) : (
          <div className="grid gap-6">
            {trending.map((topic, index) => (
              <div key={index} className="bg-white p-6 rounded-lg shadow hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      <span className="text-2xl font-bold text-gray-400">#{index + 1}</span>
                      <h3 className="text-xl font-semibold text-gray-900">{topic.topic}</h3>
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getSentimentColor(topic.sentiment_score)}`}>
                        {getSentimentLabel(topic.sentiment_score)}
                      </span>
                    </div>
                    
                    <div className="flex items-center space-x-6 text-sm text-gray-500 mb-3">
                      <div className="flex items-center">
                        <span className="font-medium text-gray-900">{topic.mentions.toLocaleString()}</span>
                        <span className="ml-1">mentions</span>
                      </div>
                      
                      <div className="flex items-center">
                        <span className="font-medium text-gray-900">
                          {topic.sentiment_score > 0 ? '+' : ''}{(topic.sentiment_score * 100).toFixed(1)}%
                        </span>
                        <span className="ml-1">sentiment</span>
                      </div>
                      
                      <div className="flex items-center">
                        <span className={`font-medium ${getGrowthColor(topic.growth_rate)}`}>
                          {topic.growth_rate.toFixed(1)}x
                        </span>
                        <span className="ml-1">growth</span>
                      </div>
                    </div>

                    {/* Platforms */}
                    <div className="flex items-center space-x-2 mb-3">
                      <span className="text-sm text-gray-500">Platforms:</span>
                      {topic.platforms.map((plt, idx) => (
                        <span key={idx} className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-800 capitalize">
                          {plt}
                        </span>
                      ))}
                    </div>

                    {/* Related Keywords */}
                    {topic.related_keywords && topic.related_keywords.length > 0 && (
                      <div className="flex items-center space-x-2">
                        <span className="text-sm text-gray-500">Related:</span>
                        <div className="flex flex-wrap gap-1">
                          {topic.related_keywords.slice(0, 5).map((keyword, idx) => (
                            <span key={idx} className="inline-flex items-center px-2 py-1 rounded text-xs bg-gray-100 text-gray-700">
                              {keyword}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Trend Indicator */}
                  <div className="flex flex-col items-center ml-4">
                    <div className={`text-2xl ${getGrowthColor(topic.growth_rate)}`}>
                      {topic.growth_rate > 1.2 ? '📈' : topic.growth_rate > 0.8 ? '➡️' : '📉'}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      {topic.growth_rate > 1.2 ? 'Rising' : topic.growth_rate > 0.8 ? 'Stable' : 'Falling'}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Summary Stats */}
        {trending.length > 0 && (
          <div className="mt-8 bg-gray-50 p-4 rounded-lg">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
              <div>
                <div className="text-2xl font-bold text-gray-900">{trending.length}</div>
                <div className="text-sm text-gray-500">Trending Topics</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-gray-900">
                  {trending.reduce((sum, topic) => sum + topic.mentions, 0).toLocaleString()}
                </div>
                <div className="text-sm text-gray-500">Total Mentions</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-gray-900">
                  {trending.filter(topic => topic.sentiment_score > 0.1).length}
                </div>
                <div className="text-sm text-gray-500">Positive Topics</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-gray-900">
                  {(trending.reduce((sum, topic) => sum + topic.growth_rate, 0) / trending.length).toFixed(1)}x
                </div>
                <div className="text-sm text-gray-500">Avg Growth</div>
              </div>
            </div>
          </div>
        )}

        {/* Last Updated */}
        <div className="mt-6 text-center text-sm text-gray-500">
          Last updated: {new Date().toLocaleString()}
        </div>
      </div>
    </div>
  );
}

export default TrendingTopics;