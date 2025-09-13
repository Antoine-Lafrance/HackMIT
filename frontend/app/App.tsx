import { StatusBar } from 'expo-status-bar';
import { StyleSheet, View } from 'react-native';
import MainApp from '../components/MainApp';

export default function App() {
  return (
    <View style={styles.container}>
      <MainApp />
      <StatusBar style="auto" />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
});
