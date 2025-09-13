import React, { useState, useRef, useEffect } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Alert, Dimensions } from 'react-native';
import { CameraView, CameraType, useCameraPermissions } from 'expo-camera';
import { Ionicons } from '@expo/vector-icons';
import * as ScreenOrientation from 'expo-screen-orientation';

interface CameraScreenProps {
    onClose?: () => void;
    onDataCapture?: (data: any) => void;
}

export default function CameraScreen({ onClose, onDataCapture }: CameraScreenProps) {
    const [facing, setFacing] = useState<CameraType>('back');
    const [permission, requestPermission] = useCameraPermissions();
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [currentTime, setCurrentTime] = useState(new Date().toLocaleTimeString());
    const cameraRef = useRef<CameraView>(null);

    useEffect(() => {
    const lockOrientation = async () => {
        await ScreenOrientation.lockAsync(ScreenOrientation.OrientationLock.LANDSCAPE);
    };
    lockOrientation();

    setIsAnalyzing(true);

    const timeInterval = setInterval(() => {
        setCurrentTime(new Date().toLocaleTimeString());
    }, 1000);

    return () => {
        ScreenOrientation.unlockAsync();
        setIsAnalyzing(false);
        clearInterval(timeInterval);
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
});