import { registerRootComponent } from 'expo';
import messaging from '@react-native-firebase/messaging';
import App from './App';

// Must be registered outside the React tree — this is what fires when the
// app is backgrounded or killed, which is the actual "silent OTP" case.
// A real build should write remoteMessage.data.code somewhere the UI can
// read on next foreground (AsyncStorage, a local notification, etc.) — this
// spike only logs it, since there is no mounted UI to update.
messaging().setBackgroundMessageHandler(async (remoteMessage) => {
  console.log('[fcm-otp-spike] background data message:', remoteMessage.data);
});

registerRootComponent(App);
