import { useState } from 'react';
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { cssInterop } from 'nativewind';

cssInterop(LinearGradient, { className: 'style' });

// Static UI only (ticket #2 scope). Phone OTP + Google OAuth logic lands in ticket #3.
export default function Login() {
  const [phone, setPhone] = useState('');

  return (
    <SafeAreaView className="flex-1 bg-white">
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} className="flex-1">
        <ScrollView
          contentContainerClassName="flex-grow justify-center px-6 py-10"
          keyboardShouldPersistTaps="handled"
        >
          <LinearGradient
            colors={['#8B5CF6', '#3B82F6', '#14B8A6']}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 1 }}
            className="h-16 w-16 items-center justify-center self-center rounded-2xl"
          >
            <Text className="text-xl font-bold text-white">SC</Text>
          </LinearGradient>

          <Text className="mt-5 text-center text-2xl font-bold text-slate-900">SearchInCircle</Text>
          <Text className="mt-1 text-center text-base text-slate-500">
            Find trusted people for what you need.
          </Text>

          <View className="mt-10">
            <Text className="mb-2 text-sm font-medium text-slate-700">Phone number</Text>
            <TextInput
              value={phone}
              onChangeText={setPhone}
              placeholder="+1 555 000 0000"
              placeholderTextColor="#94A3B8"
              keyboardType="phone-pad"
              autoComplete="tel"
              textContentType="telephoneNumber"
              accessibilityLabel="Phone number"
              className="min-h-[52px] rounded-2xl border border-slate-200 px-4 text-base text-slate-900"
            />

            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Continue"
              className="mt-4 overflow-hidden rounded-2xl active:opacity-80"
            >
              <LinearGradient
                colors={['#8B5CF6', '#3B82F6']}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 0 }}
                className="min-h-[52px] items-center justify-center"
              >
                <Text className="text-base font-semibold text-white">Continue</Text>
              </LinearGradient>
            </Pressable>
          </View>

          <View className="my-6 flex-row items-center gap-3">
            <View className="h-px flex-1 bg-slate-200" />
            <Text className="text-sm text-slate-400">or</Text>
            <View className="h-px flex-1 bg-slate-200" />
          </View>

          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Continue with Google"
            className="min-h-[52px] items-center justify-center rounded-2xl border border-slate-200 active:bg-slate-50"
          >
            <Text className="text-base font-semibold text-slate-900">Continue with Google</Text>
          </Pressable>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
