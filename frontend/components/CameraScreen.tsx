import React, { useState, useRef, useEffect } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Alert, Dimensions, Linking } from 'react-native';
import { CameraView, CameraType, useCameraPermissions } from 'expo-camera';
import { Ionicons } from '@expo/vector-icons';
import * as ScreenOrientation from 'expo-screen-orientation';
import * as Location from 'expo-location';
import * as Contacts from 'expo-contacts';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Audio } from 'expo-av';

interface CameraScreenProps {
    onClose?: () => void;
    onDataCapture?: (data: any) => void;
}

export default function CameraScreen({ onClose, onDataCapture }: CameraScreenProps) {
    const [facing, setFacing] = useState<CameraType>('back');
    const [permission, requestPermission] = useCameraPermissions();
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [currentTime, setCurrentTime] = useState(new Date().toLocaleTimeString());
    const [location, setLocation] = useState<Location.LocationObject | null>(null);
    const [address, setAddress] = useState<string>('Loading location...');
    const [homeLocation, setHomeLocation] = useState<{latitude: number, longitude: number} | null>(null);
    const [hasCheckedIfLost, setHasCheckedIfLost] = useState(false);
    const [recording, setRecording] = useState<Audio.Recording | null>(null);
    const [isRecording, setIsRecording] = useState(false);
    const [audioSegments, setAudioSegments] = useState<{uri: string, timestamp: string}[]>([]);
    const [uploadStatus, setUploadStatus] = useState<string>('');
    
    const isRecordingRef = useRef(false);
    const cameraRef = useRef<CameraView>(null);

    const calculateDistance = (lat1: number, lon1: number, lat2: number, lon2: number): number => {
        const R = 6371;
        const dLat = (lat2 - lat1) * Math.PI / 180;
        const dLon = (lon2 - lon1) * Math.PI / 180;
        const a = 
            Math.sin(dLat/2) * Math.sin(dLat/2) +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * 
            Math.sin(dLon/2) * Math.sin(dLon/2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
        return R * c;
    };

    const loadHomeLocation = async () => {
        try {
            const savedHome = await AsyncStorage.getItem('homeLocation');
            if (savedHome) {
                const homeData = JSON.parse(savedHome);
                setHomeLocation(homeData.coordinates || null);
            } else {
                console.log('No home location saved');
            }
        } catch (error) {
            console.error('Error loading home location:', error);
        }
    };

    const loadExistingAudioSegments = async () => {
        try {
            const savedAudio = await AsyncStorage.getItem('audioSegments');
            if (savedAudio) {
                const audioData = JSON.parse(savedAudio);
                setAudioSegments(audioData);
                console.log('Loaded existing audio segments:', audioData.length);
            } else {
                console.log('No existing audio segments found');
            }
        } catch (error) {
            console.error('Error loading audio segments:', error);
        }
    };

    const getHomeLocationFromStorage = async () => {
        try {
            const savedHome = await AsyncStorage.getItem('homeLocation');
            if (savedHome) {
                const homeData = JSON.parse(savedHome);
                return homeData.coordinates || null;
            }
            return null;
        } catch (error) {
            console.error('Error loading home location:', error);
            return null;
        }
    };

    const checkIfLost = async (currentLat: number, currentLon: number) => {
        if (hasCheckedIfLost) {
            return;
        }

        const loadedHomeLocation = await getHomeLocationFromStorage();
        
        if (!loadedHomeLocation) {
            return;
        }

        const distanceFromHome = calculateDistance(
            currentLat, 
            currentLon, 
            loadedHomeLocation.latitude, 
            loadedHomeLocation.longitude
        );

        const DISTANCE_THRESHOLD = 1; 
        
        if (distanceFromHome > DISTANCE_THRESHOLD) {
            setHasCheckedIfLost(true); // Only ask once per session
            
            Alert.alert(
                'Are you lost?',
                `You are ${distanceFromHome.toFixed(1)}km from your home location. Do you need help getting back?`,
                [
                    { 
                        text: 'I\'m OK', 
                        style: 'cancel',
                        onPress: () => console.log('User selected: I\'m OK')
                    },
                    { 
                        text: 'Call Caretaker', 
                        onPress: async () => {
                            console.log('User selected: Call Caretaker');
                            try {
                                const { status } = await Contacts.requestPermissionsAsync();
                                if (status === 'granted') {
                                    const { data } = await Contacts.getContactsAsync({
                                        fields: [Contacts.Fields.Name, Contacts.Fields.PhoneNumbers],
                                        name: 'Caretaker'
                                    });
                                    
                                    if (data.length > 0 && data[0].phoneNumbers && data[0].phoneNumbers.length > 0) {
                                        const phoneNumber = data[0].phoneNumbers[0].number;
                                        const phoneUrl = `tel:${phoneNumber}`;
                                        Linking.openURL(phoneUrl);
                                    } else {
                                        Alert.alert('Error', 'Caretaker contact not found or has no phone number.');
                                    }
                                } else {
                                    Alert.alert('Error', 'Cannot access contacts to call caretaker.');
                                }
                            } catch (error) {
                                Alert.alert('Error', 'Failed to call caretaker.');
                            }
                        }
                    },
                    { 
                        text: 'Get Directions Home', 
                        onPress: () => {
                            // Open maps with directions to home
                            const mapsUrl = `maps://app?daddr=${loadedHomeLocation.latitude},${loadedHomeLocation.longitude}`;
                            const googleMapsUrl = `https://www.google.com/maps/dir/?api=1&destination=${loadedHomeLocation.latitude},${loadedHomeLocation.longitude}`;
                            
                            Linking.canOpenURL(mapsUrl).then(supported => {
                                if (supported) {
                                    Linking.openURL(mapsUrl);
                                } else {
                                    Linking.openURL(googleMapsUrl);
                                }
                            });
                        }
                    }
                ]
            );
        } else {
            console.log('Not showing alert - Distance:', distanceFromHome, 'km (under threshold)');
        }
    };

    const startContinuousRecording = async () => {
        try {            
            const { status } = await Audio.requestPermissionsAsync();
            if (status !== 'granted') {
                return;
            }
            await Audio.setAudioModeAsync({
                allowsRecordingIOS: true,
                playsInSilentModeIOS: true,
            });
            setIsRecording(true);
            isRecordingRef.current = true;
            startRecordingSegment();
        } catch (error) {
            console.error('Failed');
        }
    };

    const startRecordingSegment = async () => {
        try {
            const { recording: recordingInstance } = await Audio.Recording.createAsync(
                Audio.RecordingOptionsPresets.LOW_QUALITY
            );
            
            setRecording(recordingInstance);
            console.log('Recording segment started - 3 second timer set');

            setTimeout(async () => {
                await processRecordingSegment(recordingInstance);
            }, 3000);

        } catch (error) {
            // Retry after delay if still recording
            if (isRecordingRef.current) {
                setTimeout(() => {
                    startRecordingSegment();
                }, 2000);
            }
        }
    };

    const processRecordingSegment = async (recordingInstance: Audio.Recording) => {
        try {
            await recordingInstance.stopAndUnloadAsync();
            const uri = recordingInstance.getURI();
            
            if (uri) {
                console.log('🎵 Audio segment saved:', uri);
                const audioSegment = { uri, timestamp: new Date().toISOString() };
                setAudioSegments(prev => {
                    const newSegments = [...prev, audioSegment];           
                    //Persist to async storage         
                    AsyncStorage.setItem('audioSegments', JSON.stringify(newSegments))
                        .catch(error => console.error('Failed to save audio segments:', error));
                    return newSegments;
                });
            }
            if (isRecordingRef.current) {
                startRecordingSegment();
            } else {
                console.log('Stopped recording');
            }
        } catch (error) {
            if (isRecordingRef.current) {
                setTimeout(startRecordingSegment, 1000);
            }
        }
    };

    const stopContinuousRecording = async () => {
        try {
            console.log('Stopped recording');
            setIsRecording(false);
            isRecordingRef.current = false;
            
            if (recording) {
                await recording.stopAndUnloadAsync();
                setRecording(null);
            }
            
            await Audio.setAudioModeAsync({
                allowsRecordingIOS: false,
            });
            
            try {
                const savedAudio = await AsyncStorage.getItem('audioSegments');
                if (savedAudio) {
                    const audioData = JSON.parse(savedAudio);
                    console.log(`📂 Recording session ended. Total segments saved: ${audioData.length}`);
                } 
            } catch (storageError) {
                console.error('Failed to read audio segments from storage:', storageError);
            }
        } catch (error) {
            console.error('Failed to stop recording:', error);
        }
    };

    const getAllAudioSegments = async () => {
        try {
            const savedAudio = await AsyncStorage.getItem('audioSegments');
            if (savedAudio) {
                const audioData = JSON.parse(savedAudio);
                console.log('All recorded audio segments from storage:', audioData);
                return audioData;
            } else {
                console.log('📂 No audio segments found in storage');
                return [];
            }
        } catch (error) {
            console.error('Error loading audio segments:', error);
            return [];
        }
    };

    const clearAllAudioSegments = async () => {
        try {
            await AsyncStorage.removeItem('audioSegments');
            setAudioSegments([]);
            console.log('Delete');
        } catch (error) {
            console.error('Failed to clear audio segments:', error);
        }
    };

    // Function to convert audio file to base64
    const convertAudioToBase64 = async (audioUri: string): Promise<string | null> => {
        try {
            console.log('Converting audio to base64:', audioUri);
            
            // Use fetch to read the file as blob
            const response = await fetch(audioUri);
            const blob = await response.blob();
            
            // Convert blob to base64
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onloadend = () => {
                    if (reader.result) {
                        const base64 = reader.result.toString().split(',')[1] || reader.result.toString();
                        console.log('Audio converted to base64, length:', base64.length);
                        resolve(base64);
                    } else {
                        reject(new Error('Failed to convert audio to base64'));
                    }
                };
                reader.onerror = reject;
                reader.readAsDataURL(blob);
            });
        } catch (error) {
            console.error('Failed to convert audio to base64:', error);
            return null;
        }
    };
    const uploadAudioSegment = async (audioUri: string, timestamp: string) => {
        try {
            console.log('Uploading audio segment and camera capture to agent');
            // Capture photo from camera first
            let photoUri = null;
            let photoBase64 = null;
            if (cameraRef.current) {
                try {
                    console.log('Capturing photo from camera');
                    const photo = await cameraRef.current.takePictureAsync({
                        quality: 0.7,
                        base64: true,
                        skipProcessing: true,
                    });
                    photoUri = photo.uri;
                    photoBase64 = photo.base64;
                    console.log('Photo captured:', photoUri);
                } catch (photoError) {
                    console.error('Failed to capture photo:', photoError);
                }
            }
            
            let audioBase64 = null;
            if (audioUri) {
                audioBase64 = await convertAudioToBase64(audioUri);
            }
            const response = await fetch('https://antlaf6--minimalist-anthropic-agent-analyze-context--81a139-dev.modal.run/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    image_data: photoBase64,
                    audio_data: audioBase64
                }),
            });
            
            if (response.ok) {
                const result = await response.json();
                console.log('Success');
                return result;
            } else {
                let errorText = '';
                try {
                    errorText = await response.text();
                } catch (e) {
                }
                console.error('Failed', response.status, response.statusText, errorText);
                return null;
            }
        } catch (error) {
            console.error('Failed', error);
            return null;
        }
    };

    // Compress and upload latest audio
    const compressAndUploadLatest = async () => {
        try {
            setUploadStatus('Finding latest audio');
            const allSegments = await getAllAudioSegments();
            if (allSegments.length === 0) {
                setUploadStatus('No audio segments to upload');
                setTimeout(() => setUploadStatus(''), 3000);
                return;
            }
            
            const latest = allSegments[allSegments.length - 1];
            setUploadStatus('Uploading latest audio');
            const result = await uploadAudioSegment(latest.uri, latest.timestamp);
            
            if (result) {
                setUploadStatus(' Latest audio uploaded!');
                console.log('Latest audio compressed and uploaded successfully');
            } else {
                setUploadStatus('Upload failed');
            }
            setTimeout(() => setUploadStatus(''), 3000);
            return result;
        } catch (error) {
            console.error('Failed to compress and upload latest audio:', error);
            setUploadStatus(' Upload error');
            setTimeout(() => setUploadStatus(''), 3000);
            return null;
        }
    };

    // Quick access function for debugging
    const logAllAudioSegments = async () => {
        try {
            const savedAudio = await AsyncStorage.getItem('audioSegments');
            if (savedAudio) {
                const audioData = JSON.parse(savedAudio);
                console.log(' === AUDIO SEGMENTS SUMMARY ===');
                console.log(`Total segments: ${audioData.length}`);
                audioData.forEach((segment: {uri: string, timestamp: string}, index: number) => {
                    console.log(` ${index + 1}. ${segment.uri} (${segment.timestamp})`);
                });
                console.log('=== END SUMMARY ===');
                return audioData;
            } else {
                console.log(' No audio segments found in storage');
                return [];
            }
        } catch (error) {
            console.error('Error loading audio segments:', error);
            return [];
        }
    };

    // Function to play an audio segment
    const playAudioSegment = async (uri: string) => {
        try {
            console.log('Playing audio:', uri);
            const { sound } = await Audio.Sound.createAsync({ uri });
            await sound.playAsync();
            console.log('Audio playback started');
            
            // Clean up when done
            sound.setOnPlaybackStatusUpdate((status) => {
                if (status.isLoaded && status.didJustFinish) {
                    sound.unloadAsync();
                    console.log('Audio playback finished');
                }
            });
        } catch (error) {
            console.error('Failed to play audio:', error);
        }
    };

    // Function to play the latest recorded audio
    const playLatestAudio = async () => {
        try {
            const savedAudio = await AsyncStorage.getItem('audioSegments');
            if (savedAudio) {
                const audioData = JSON.parse(savedAudio);
                if (audioData.length > 0) {
                    const latest = audioData[audioData.length - 1];
                    console.log('Playing latest audio segment...');
                    await playAudioSegment(latest.uri);
                } else {
                    console.log('No audio segments to play');
                }
            } else {
                console.log('No audio segments found');
            }
        } catch (error) {
            console.error('Failed to play latest audio:', error);
        }
    };

    // Expose function to global scope for easy testing
    if (typeof global !== 'undefined') {
        (global as any).logAllAudioSegments = logAllAudioSegments;
        (global as any).clearAllAudioSegments = clearAllAudioSegments;
        (global as any).playAudioSegment = playAudioSegment;
        (global as any).playLatestAudio = playLatestAudio;
    }

    useEffect(() => {
    console.log('🚀 CameraScreen useEffect started');
    const lockOrientation = async () => {
        await ScreenOrientation.lockAsync(ScreenOrientation.OrientationLock.LANDSCAPE);
    };
    lockOrientation();

    setIsAnalyzing(true);
    loadHomeLocation();
    loadExistingAudioSegments();
    
    console.log('🎤 About to start continuous audio recording...');
    // Start continuous audio recording
    startContinuousRecording();

    const timeInterval = setInterval(() => {
        setCurrentTime(new Date().toLocaleTimeString());
    }, 1000);

    const getLocation = async () => {
        try {
            let { status } = await Location.requestForegroundPermissionsAsync();
            if (status !== 'granted') {
                setAddress('Location permission denied');
                return;
            }

            let currentLocation = await Location.getCurrentPositionAsync({});
            setLocation(currentLocation);
            setTimeout(() => {
                checkIfLost(currentLocation.coords.latitude, currentLocation.coords.longitude);
            }, 2000);

            let reverseGeocode = await Location.reverseGeocodeAsync({
                latitude: currentLocation.coords.latitude,
                longitude: currentLocation.coords.longitude,
            });

            if (reverseGeocode.length > 0) {
                const addr = reverseGeocode[0];
                const formattedAddress = `${addr.street || ''} ${addr.city || ''}, ${addr.region || ''}`.trim();
                setAddress(formattedAddress || 'Address unavailable');
            } else {
                setAddress(`${currentLocation.coords.latitude.toFixed(4)}, ${currentLocation.coords.longitude.toFixed(4)}`);
            }
        } catch (error) {
            console.error('Error getting location:', error);
            setAddress('Location unavailable');
        }
    };

    getLocation();

    return () => {
        ScreenOrientation.unlockAsync();
        setIsAnalyzing(false);
        clearInterval(timeInterval);
        
        // Stop continuous recording when component unmounts
        stopContinuousRecording();
    };
    }, []);

    if (!permission) {
        return <View style={styles.container} />;
    }

    if (!permission.granted) {
    return (
        <View style={styles.container}>
        <View style={styles.permissionContainer}>
            <Text style={styles.message}>Camera access required for smart glasses mode</Text>
            <TouchableOpacity style={styles.button} onPress={requestPermission}>
            <Text style={styles.buttonText}>Grant Permission</Text>
            </TouchableOpacity>
        </View>
        </View>
    );
    }

    const handleExit = async () => {
        if (onClose) {
            await ScreenOrientation.unlockAsync();
            onClose();
        }
    };

    return (
        <View style={styles.container}>
            <CameraView 
                style={styles.camera} 
                facing={facing}
                ref={cameraRef}
            >
            <View style={styles.topOverlay}>
                <View style={styles.statusContainer}>
                <View style={styles.statusItem}>
                    <View style={[styles.statusDot, { backgroundColor: isAnalyzing ? '#00ff00' : '#ff0000' }]} />
                    <Text style={styles.statusText}>
                    {isAnalyzing ? 'ANALYZING' : 'STANDBY'}
                    </Text>
                </View>
                <Text style={styles.timeText}>
                    {currentTime}
                </Text>
                <View style={styles.locationItem}>
                    <Ionicons name="location-outline" size={12} color="white" />
                    <Text style={styles.locationText}>
                    {address}
                    </Text>
                </View>
                </View>
                
                <TouchableOpacity style={styles.exitButton} onPress={handleExit}>
                <Ionicons name="close" size={24} color="white" />
                </TouchableOpacity>
            </View>

            <View style={styles.bottomOverlay}>
                <View style={styles.glassesInfo}>
                <Text style={styles.glassesText}>Smart Glasses Mode</Text>
                <Text style={styles.glassesSubtext}>Here are your surroundings</Text>
                </View>
                
                <View style={styles.audioInfo}>
                <View style={styles.audioStatus}>
                    <View style={[styles.recordingDot, { backgroundColor: isRecording ? '#ff4444' : '#666666' }]} />
                    <Text style={styles.audioStatusText}>
                    {isRecording ? 'RECORDING' : 'AUDIO READY'}
                    </Text>
                </View>
                
                {uploadStatus ? (
                    <View style={styles.uploadStatus}>
                        <Text style={styles.uploadStatusText}>{uploadStatus}</Text>
                    </View>
                ) : null}
                
                <View style={styles.audioControlPanel}>
                    
                    <TouchableOpacity 
                        style={[styles.audioButton, styles.uploadButton]}
                        onPress={compressAndUploadLatest}
                    >
                        <Text style={styles.audioButtonText}>📤</Text>
                    </TouchableOpacity>
                    
                    
                    <TouchableOpacity 
                        style={[styles.audioButton, styles.clearButton]}
                        onPress={clearAllAudioSegments}
                    >
                        <Text style={styles.audioButtonText}>🗑️</Text>
                    </TouchableOpacity>
                </View>
                </View>
            </View>

            <View style={styles.crosshair}>
                <View style={styles.crosshairHorizontal} />
                <View style={styles.crosshairVertical} />
            </View>
            </CameraView>
        </View>
    );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
  },
  permissionContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  message: {
    textAlign: 'center',
    paddingBottom: 20,
    color: 'white',
    fontSize: 16,
  },
  camera: {
    flex: 1,
  },
  topOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    padding: 20,
    paddingTop: 40,
    backgroundColor: 'rgba(0, 0, 0, 0.3)',
  },
  statusContainer: {
    flexDirection: 'column',
  },
  statusItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 5,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 8,
  },
  statusText: {
    color: 'white',
    fontSize: 12,
    fontWeight: 'bold',
  },
  timeText: {
    color: 'white',
    fontSize: 12,
    opacity: 0.8,
  },
  locationItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 5,
  },
  locationText: {
    color: 'white',
    fontSize: 11,
    opacity: 0.8,
    marginLeft: 4,
    maxWidth: 200,
  },
  exitButton: {
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    borderRadius: 20,
    padding: 8,
  },
  bottomOverlay: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    padding: 20,
    backgroundColor: 'rgba(0, 0, 0, 0.3)',
  },
  glassesInfo: {
    alignItems: 'center',
  },
  glassesText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
  },
  glassesSubtext: {
    color: 'white',
    fontSize: 12,
    opacity: 0.8,
    marginTop: 4,
  },
  crosshair: {
    position: 'absolute',
    top: '50%',
    left: '50%',
    width: 30,
    height: 30,
    marginTop: -15,
    marginLeft: -15,
  },
  crosshairHorizontal: {
    position: 'absolute',
    top: '50%',
    left: 0,
    right: 0,
    height: 1,
    backgroundColor: 'rgba(255, 255, 255, 0.8)',
  },
  crosshairVertical: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    left: '50%',
    width: 1,
    backgroundColor: 'rgba(255, 255, 255, 0.8)',
  },
  button: {
    backgroundColor: '#007AFF',
    padding: 15,
    borderRadius: 8,
    margin: 20,
  },
  buttonText: {
    color: 'white',
    textAlign: 'center',
    fontSize: 16,
    fontWeight: '600',
  },
  audioInfo: {
    alignItems: 'center',
    marginTop: 15,
  },
  audioStatus: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  recordingDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 8,
  },
  audioStatusText: {
    color: 'white',
    fontSize: 12,
    fontWeight: 'bold',
  },
  audioControlPanel: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: 10,
    marginTop: 10,
  },
  audioButton: {
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    borderRadius: 20,
    padding: 8,
    minWidth: 40,
    alignItems: 'center',
    justifyContent: 'center',
  },
  audioButtonText: {
    color: 'white',
    fontSize: 16,
    textAlign: 'center',
  },
  uploadButton: {
    backgroundColor: 'rgba(0, 122, 255, 0.3)',
  },
  uploadAllButton: {
    backgroundColor: 'rgba(52, 199, 89, 0.3)',
  },
  clearButton: {
    backgroundColor: 'rgba(255, 59, 48, 0.3)',
  },
  uploadStatus: {
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    borderRadius: 15,
    paddingHorizontal: 12,
    paddingVertical: 6,
    marginVertical: 5,
  },
  uploadStatusText: {
    color: 'white',
    fontSize: 11,
    fontWeight: '500',
    textAlign: 'center',
  },
});