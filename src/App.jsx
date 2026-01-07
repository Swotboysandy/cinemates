import React, { useState, useEffect, useRef, useCallback } from 'react';
import Peer from 'peerjs';
import { Link as LinkIcon, Phone, Video, Mic, MicOff, VideoOff, MonitorPlay } from 'lucide-react';

// Helper to extract YouTube video ID from URL
const getYouTubeId = (url) => {
  if (!url) return null;
  const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|&v=)([^#&?]*).*/;
  const match = url.match(regExp);
  return (match && match[2].length === 11) ? match[2] : null;
};

// Check if URL is a direct video file
const isDirectVideo = (url) => {
  if (!url) return false;
  return /\.(mp4|webm|ogg|m3u8)($|\?)/.test(url.toLowerCase());
};

function App() {
  const [myId, setMyId] = useState('');
  const [remoteId, setRemoteId] = useState('');
  const [conn, setConn] = useState(null);
  const [call, setCall] = useState(null);
  const [stream, setStream] = useState(null);
  const [remoteStream, setRemoteStream] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [videoUrl, setVideoUrl] = useState('https://www.youtube.com/watch?v=xE3ZJIovVVE');
  const [inputUrl, setInputUrl] = useState('');
  const [playerReady, setPlayerReady] = useState(false);

  // Media states
  const [isMicOn, setIsMicOn] = useState(true);
  const [isCamOn, setIsCamOn] = useState(true);

  // Refs
  const videoRef = useRef(null); // For direct video
  const ytPlayerRef = useRef(null); // YouTube player instance
  const myVideoRef = useRef(null);
  const remoteVideoRef = useRef(null);
  const isRemoteUpdate = useRef(false);
  const peerInstance = useRef(null);
  const connRef = useRef(null);
  const lastSyncTime = useRef(0);

  // Load YouTube IFrame API
  useEffect(() => {
    // Check if API is already loaded
    if (window.YT && window.YT.Player) {
      return;
    }

    // Create script tag
    const tag = document.createElement('script');
    tag.src = 'https://www.youtube.com/iframe_api';
    const firstScriptTag = document.getElementsByTagName('script')[0];
    firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

    // API will call this when ready
    window.onYouTubeIframeAPIReady = () => {
      console.log('YouTube IFrame API Ready');
    };
  }, []);

  // Initialize YouTube player when video URL changes
  useEffect(() => {
    const youtubeId = getYouTubeId(videoUrl);
    if (!youtubeId) return;

    // Wait for API to load
    const initPlayer = () => {
      if (!window.YT || !window.YT.Player) {
        setTimeout(initPlayer, 100);
        return;
      }

      // Destroy existing player
      if (ytPlayerRef.current) {
        ytPlayerRef.current.destroy();
      }

      // Create new player
      ytPlayerRef.current = new window.YT.Player('youtube-player', {
        videoId: youtubeId,
        playerVars: {
          autoplay: 0,
          controls: 1,
          modestbranding: 1,
          rel: 0,
          enablejsapi: 1,
          origin: window.location.origin,
        },
        events: {
          onReady: (event) => {
            console.log('YouTube Player Ready');
            setPlayerReady(true);
          },
          onStateChange: (event) => {
            handlePlayerStateChange(event.data);
          },
        },
      });
    };

    initPlayer();

    return () => {
      if (ytPlayerRef.current) {
        ytPlayerRef.current.destroy();
        ytPlayerRef.current = null;
      }
    };
  }, [videoUrl]);

  // Handle YouTube player state changes
  const handlePlayerStateChange = (state) => {
    if (isRemoteUpdate.current) return;

    const player = ytPlayerRef.current;
    if (!player) return;

    const currentTime = player.getCurrentTime();

    // Debounce sync events
    const now = Date.now();
    if (now - lastSyncTime.current < 500) return;
    lastSyncTime.current = now;

    switch (state) {
      case window.YT.PlayerState.PLAYING:
        console.log('Local: Playing at', currentTime);
        sendData({ type: 'play', time: currentTime });
        break;
      case window.YT.PlayerState.PAUSED:
        console.log('Local: Paused at', currentTime);
        sendData({ type: 'pause', time: currentTime });
        break;
      case window.YT.PlayerState.BUFFERING:
        // Could send seeking event here if needed
        break;
    }
  };

  // PeerJS initialization
  useEffect(() => {
    const peer = new Peer();
    peerInstance.current = peer;

    peer.on('open', (id) => {
      setMyId(id);
      console.log('My Peer ID:', id);
    });

    peer.on('connection', (connection) => {
      console.log('Incoming data connection');
      handleConnection(connection);
    });

    peer.on('call', (incomingCall) => {
      console.log('Incoming media call');
      navigator.mediaDevices.getUserMedia({ video: true, audio: true })
        .then((mediaStream) => {
          setStream(mediaStream);
          if (myVideoRef.current) myVideoRef.current.srcObject = mediaStream;

          incomingCall.answer(mediaStream);
          handleCall(incomingCall);
        })
        .catch(err => {
          console.error('Failed to get media:', err);
          incomingCall.answer(null);
          handleCall(incomingCall);
        });
    });

    peer.on('error', (err) => {
      console.error('Peer error:', err);
    });

    return () => {
      peer.destroy();
    };
  }, []);

  const connectToPeer = () => {
    if (!remoteId || !peerInstance.current) return;

    const connection = peerInstance.current.connect(remoteId);
    handleConnection(connection);

    navigator.mediaDevices.getUserMedia({ video: true, audio: true })
      .then((mediaStream) => {
        setStream(mediaStream);
        if (myVideoRef.current) myVideoRef.current.srcObject = mediaStream;
        const mediaCall = peerInstance.current.call(remoteId, mediaStream);
        handleCall(mediaCall);
      })
      .catch(err => {
        console.error('Failed to get media:', err);
      });
  };

  const handleConnection = useCallback((connection) => {
    connRef.current = connection;
    setConn(connection);

    connection.on('open', () => {
      console.log('Data connection open');
      setIsConnected(true);
    });

    connection.on('data', (data) => {
      handleData(data);
    });

    connection.on('close', () => {
      console.log('Connection closed');
      setIsConnected(false);
      setConn(null);
      connRef.current = null;
    });

    connection.on('error', (err) => {
      console.error('Connection error:', err);
    });
  }, []);

  const handleCall = (mediaCall) => {
    setCall(mediaCall);

    mediaCall.on('stream', (remoteMediaStream) => {
      console.log('Received remote stream');
      setRemoteStream(remoteMediaStream);
      if (remoteVideoRef.current) remoteVideoRef.current.srcObject = remoteMediaStream;
    });

    mediaCall.on('close', () => {
      setRemoteStream(null);
    });
  };

  const handleData = (data) => {
    console.log('Received data:', data);
    isRemoteUpdate.current = true;

    const player = ytPlayerRef.current;
    const video = videoRef.current;

    switch (data.type) {
      case 'play':
        if (player && player.playVideo) {
          // Sync time first if difference is > 1 second
          const currentTime = player.getCurrentTime();
          if (Math.abs(currentTime - data.time) > 1) {
            player.seekTo(data.time, true);
          }
          player.playVideo();
          console.log('Remote: Playing at', data.time);
        } else if (video) {
          if (Math.abs(video.currentTime - data.time) > 1) {
            video.currentTime = data.time;
          }
          video.play();
        }
        break;

      case 'pause':
        if (player && player.pauseVideo) {
          player.pauseVideo();
          const currentTime = player.getCurrentTime();
          if (Math.abs(currentTime - data.time) > 1) {
            player.seekTo(data.time, true);
          }
          console.log('Remote: Paused at', data.time);
        } else if (video) {
          video.pause();
          if (Math.abs(video.currentTime - data.time) > 1) {
            video.currentTime = data.time;
          }
        }
        break;

      case 'seek':
        if (player && player.seekTo) {
          player.seekTo(data.time, true);
          console.log('Remote: Seeked to', data.time);
        } else if (video) {
          video.currentTime = data.time;
        }
        break;

      case 'url':
        setVideoUrl(data.url);
        console.log('Remote: Changed URL to', data.url);
        break;
    }

    setTimeout(() => {
      isRemoteUpdate.current = false;
    }, 1000);
  };

  const sendData = (data) => {
    if (connRef.current && connRef.current.open) {
      connRef.current.send(data);
      console.log('Sent data:', data);
    }
  };

  const changeUrl = () => {
    if (inputUrl) {
      setVideoUrl(inputUrl);
      setPlayerReady(false);
      sendData({ type: 'url', url: inputUrl });
      setInputUrl('');
    }
  };

  // Sync button - manually sync current position
  const syncNow = () => {
    const player = ytPlayerRef.current;
    if (player && player.getCurrentTime) {
      const time = player.getCurrentTime();
      const state = player.getPlayerState();
      sendData({
        type: state === window.YT.PlayerState.PLAYING ? 'play' : 'pause',
        time
      });
    }
  };

  const toggleMic = () => {
    if (stream) {
      stream.getAudioTracks().forEach(track => track.enabled = !track.enabled);
      setIsMicOn(!isMicOn);
    }
  };

  const toggleCam = () => {
    if (stream) {
      stream.getVideoTracks().forEach(track => track.enabled = !track.enabled);
      setIsCamOn(!isCamOn);
    }
  };

  const copyId = () => {
    navigator.clipboard.writeText(myId);
    alert("ID copied to clipboard!");
  };

  // Determine video type
  const youtubeId = getYouTubeId(videoUrl);
  const isDirect = isDirectVideo(videoUrl);

  return (
    <div className="container">
      {/* Header / Connection Panel */}
      <div className="glass connection-panel">
        <div className="header-info">
          <h1 className="app-title">Cinemates</h1>
          <div className="id-display">
            <span className="text-secondary">My ID:</span>
            <code className="id-code">{myId || 'Connecting...'}</code>
            <button className="btn btn-secondary btn-icon" onClick={copyId}>
              <LinkIcon size={14} />
            </button>
          </div>
        </div>

        <div className="connect-form">
          <input
            type="text"
            placeholder="Enter friend's ID to connect"
            value={remoteId}
            onChange={(e) => setRemoteId(e.target.value)}
          />
          <button className="btn" onClick={connectToPeer}>
            <Phone size={18} /> Connect
          </button>
        </div>

        <div className={`status-badge ${isConnected ? 'status-connected' : 'status-disconnected'}`}>
          {isConnected ? 'Connected' : 'Disconnected'}
        </div>
      </div>

      <div className="main-grid">

        {/* Main Content */}
        <div className="video-section">
          <div className="glass video-container">
            {youtubeId ? (
              <div id="youtube-player" className="main-video"></div>
            ) : isDirect ? (
              <video
                ref={videoRef}
                className="main-video"
                src={videoUrl}
                controls
                onPlay={() => {
                  if (!isRemoteUpdate.current && videoRef.current) {
                    sendData({ type: 'play', time: videoRef.current.currentTime });
                  }
                }}
                onPause={() => {
                  if (!isRemoteUpdate.current && videoRef.current) {
                    sendData({ type: 'pause', time: videoRef.current.currentTime });
                  }
                }}
                onSeeked={() => {
                  if (!isRemoteUpdate.current && videoRef.current) {
                    sendData({ type: 'seek', time: videoRef.current.currentTime });
                  }
                }}
              />
            ) : (
              <div className="main-video" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#9ca3af' }}>
                <p>Paste a YouTube or MP4 URL below</p>
              </div>
            )}
          </div>

          <div className="glass input-group">
            <input
              type="text"
              placeholder="Paste video URL (YouTube, MP4, etc.)"
              value={inputUrl}
              onChange={e => setInputUrl(e.target.value)}
            />
            <button className="btn" onClick={changeUrl}>
              <MonitorPlay size={18} /> Load
            </button>
            {isConnected && (
              <button className="btn btn-secondary" onClick={syncNow} title="Sync position with partner">
                🔄 Sync
              </button>
            )}
          </div>
        </div>

        {/* Sidebar */}
        <div className="sidebar">
          <div className="webcam-grid">
            {/* Local User */}
            <div className="glass webcam-feed">
              <video ref={myVideoRef} autoPlay muted playsInline />
              <div className="webcam-label">You</div>
              {!stream && <div className="camera-off-placeholder">Camera Off</div>}
              <div className="webcam-controls">
                <button onClick={toggleMic} className="btn btn-secondary btn-icon-sm">
                  {isMicOn ? <Mic size={14} /> : <MicOff size={14} />}
                </button>
                <button onClick={toggleCam} className="btn btn-secondary btn-icon-sm">
                  {isCamOn ? <Video size={14} /> : <VideoOff size={14} />}
                </button>
              </div>
            </div>

            {/* Remote User */}
            <div className="glass webcam-feed">
              <video ref={remoteVideoRef} autoPlay playsInline />
              <div className="webcam-label">Partner</div>
              {!remoteStream && <div className="camera-off-placeholder">Waiting...</div>}
            </div>
          </div>

          {/* Instructions */}
          <div className="glass info-panel">
            <h3>Instructions</h3>
            <ul>
              <li>Share your ID with a friend.</li>
              <li>Paste their ID and click Connect.</li>
              <li>Allow camera/microphone permissions.</li>
              <li>Paste a video URL to watch together.</li>
              <li><strong>Play/Pause syncs automatically!</strong></li>
              <li>Use 🔄 Sync button if out of sync.</li>
            </ul>
          </div>
        </div>

      </div>
    </div>
  );
}

export default App;
