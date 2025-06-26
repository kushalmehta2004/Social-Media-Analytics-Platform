import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, AreaChart, Area } from 'recharts';
import toast from 'react-hot-toast';

const COLORS = {
  positive: '#10B981',
  negative: '#EF4444',
  neutral: '#6B7280'
};

function SentimentAnalysis() {
  const [sentimentData, setSentimentData] = useState(null);
  const [timeSeriesData, setTimeSeriesData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [timeframe, setTimeframe] = useState('24');
  const [platform, setPlatform] = useState('all');

  useEffect(() => {
    fetchSentimentData();
    fetchTimeSeriesData();
  }, [timeframe, platform]);

  const fetchSentimentData = async () => {
    try {
      const params = new URLSearchParams({
        hours: timeframe
      });
      
      if (platform !== 'all') {
        params.append('platform', platform);
      }

      const response = await fetch(`/analytics/sentiment-overview?${params}`);
      if (response.ok) {
        const data = await response.json();
        setSentimentData(data.data);
      } else {
        throw new Error('Failed to fetch sentiment data');
      }
    } catch (error) {
      console.error('Error:', error);
      toast.error('Failed to load sentiment data');
    }
  };

  const fetchTimeSeriesData = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        hours: timeframe,
        interval: timeframe <= 6 ? '15m' : timeframe <= 24 ? '1h' : '6h'
      });
      
      if (platform !== 'all') {
        params.append('platform', platform);
      }

      const response = await fetch(`/analytics/time-series/sentiment_trend?${params}`);
      if (response.ok) {
        const data = await response.json();
        setTimeSeriesData(data.data.time_series || []);
      } else {
        throw new Error('Failed to fetch time series data');
      }
    } catch (error) {
      console.error('Error:', error);
      toast.error('Failed to load time series data');
    } finally {
      setLoading(false);
    }
  };

  const pieData = sentimentData?.distribution ? [
    { name: 'Positive', value: sentimentData.distribution.positive.count, color: COLORS.positive },
    { name: 'Negative', value: sentimentData.distribution.negative.count, color: COLORS.negative },
    { name: 'Neutral', value: sentimentData.distribution.neutral.count, color: COLORS.neutral }
  ] : [];

  const formatTimeSeriesData = (data) => {
    return data.map(item => ({
      ...item,
      timestamp: new Date(item.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}),
      positive: item.positive || 0,
      negative: item.negative || 0,
      neutral: item.neutral || 0
    }));
  };

  if (loading && !sentimentData) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="px-4 py-6 sm:px-0">
      <div className="border-4 border-dashed border-gray-200 rounded-lg p-6">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Sentiment Analysis</h1>
          
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

        {/* Summary Cards */}
        {sentimentData && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-gray-500 rounded-md flex items-center justify-center">
                      <span className="text-white font-bold">T</span>
                    </div>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">Total Posts</dt>
                      <dd className="text-lg font-medium text-gray-900">{sentimentData.total_posts.toLocaleString()}</dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-green-500 rounded-md flex items-center justify-center">
                      <span className="text-white font-bold">+</span>
                    </div>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">Positive</dt>
                      <dd className="text-lg font-medium text-gray-900">
                        {sentimentData.distribution.positive.percentage.toFixed(1)}%
                      </dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-red-500 rounded-md flex items-center justify-center">
                      <span className="text-white font-bold">-</span>
                    </div>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">Negative</dt>
                      <dd className="text-lg font-medium text-gray-900">
                        {sentimentData.distribution.negative.percentage.toFixed(1)}%
                      </dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-white overflow-hidden shadow rounded-lg">
              <div className="p-5">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-blue-500 rounded-md flex items-center justify-center">
                      <span className="text-white font-bold">~</span>
                    </div>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">Neutral</dt>
                      <dd className="text-lg font-medium text-gray-900">
                        {sentimentData.distribution.neutral.percentage.toFixed(1)}%
                      </dd>
                    </dl>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          {/* Sentiment Distribution Pie Chart */}
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Sentiment Distribution</h3>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip formatter={(value) => [value.toLocaleString(), 'Posts']} />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Sentiment Trend Over Time */}
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Sentiment Trend</h3>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={formatTimeSeriesData(timeSeriesData)}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="timestamp" />
                <YAxis />
                <Tooltip />
                <Area type="monotone" dataKey="positive" stackId="1" stroke={COLORS.positive} fill={COLORS.positive} fillOpacity={0.6} />
                <Area type="monotone" dataKey="neutral" stackId="1" stroke={COLORS.neutral} fill={COLORS.neutral} fillOpacity={0.6} />
                <Area type="monotone" dataKey="negative" stackId="1" stroke={COLORS.negative} fill={COLORS.negative} fillOpacity={0.6} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Detailed Sentiment Lines */}
        <div className="bg-white p-6 rounded-lg shadow mb-8">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Sentiment Trends (Separate Lines)</h3>
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={formatTimeSeriesData(timeSeriesData)}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="timestamp" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="positive" stroke={COLORS.positive} strokeWidth={2} name="Positive" />
              <Line type="monotone" dataKey="negative" stroke={COLORS.negative} strokeWidth={2} name="Negative" />
              <Line type="monotone" dataKey="neutral" stroke={COLORS.neutral} strokeWidth={2} name="Neutral" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Sentiment Insights */}
        {sentimentData && (
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Key Insights</h3>
            <div className="space-y-4">
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0 w-2 h-2 bg-blue-500 rounded-full mt-2"></div>
                <div>
                  <p className="text-sm text-gray-700">
                    <strong>Overall Sentiment:</strong> {' '}
                    {sentimentData.distribution.positive.percentage > 50 ? 'Predominantly positive' :
                     sentimentData.distribution.negative.percentage > 50 ? 'Predominantly negative' :
                     'Mixed sentiment'} with {sentimentData.total_posts.toLocaleString()} total posts analyzed.
                  </p>
                </div>
              </div>
              
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0 w-2 h-2 bg-green-500 rounded-full mt-2"></div>
                <div>
                  <p className="text-sm text-gray-700">
                    <strong>Positive Sentiment:</strong> {' '}
                    {sentimentData.distribution.positive.count.toLocaleString()} posts ({sentimentData.distribution.positive.percentage.toFixed(1)}%) 
                    show positive sentiment.
                  </p>
                </div>
              </div>
              
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0 w-2 h-2 bg-red-500 rounded-full mt-2"></div>
                <div>
                  <p className="text-sm text-gray-700">
                    <strong>Negative Sentiment:</strong> {' '}
                    {sentimentData.distribution.negative.count.toLocaleString()} posts ({sentimentData.distribution.negative.percentage.toFixed(1)}%) 
                    show negative sentiment.
                  </p>
                </div>
              </div>
              
              <div className="flex items-start space-x-3">
                <div className="flex-shrink-0 w-2 h-2 bg-gray-500 rounded-full mt-2"></div>
                <div>
                  <p className="text-sm text-gray-700">
                    <strong>Platform Coverage:</strong> {' '}
                    Analysis covers {platform === 'all' ? 'all platforms' : platform} over the last {timeframe} hours.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Last Updated */}
        <div className="mt-6 text-center text-sm text-gray-500">
          Last updated: {sentimentData?.last_updated ? new Date(sentimentData.last_updated).toLocaleString() : 'Never'}
        </div>
      </div>
    </div>
  );
}

export default SentimentAnalysis;