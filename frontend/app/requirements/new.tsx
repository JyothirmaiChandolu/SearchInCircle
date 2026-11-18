import { useEffect, useState } from 'react';
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Feather } from '@expo/vector-icons';
import { router } from 'expo-router';
import { ChipInput } from '../../src/components/ChipInput';
import { PrimaryButton } from '../../src/components/PrimaryButton';
import { AURORA } from '../../src/lib/theme';
import { ApiError, createRequirement, getValidSession, type WorkType } from '../../src/lib/api';

const inputStyle = { backgroundColor: '#fff', borderWidth: 1, borderColor: AURORA.line, color: AURORA.ink };

export default function NewRequirement() {
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [skillsNeeded, setSkillsNeeded] = useState<string[]>([]);
  const [workType, setWorkType] = useState<WorkType>('REMOTE');
  const [experienceRequired, setExperienceRequired] = useState('');
  const [salary, setSalary] = useState('');
  const [location, setLocation] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      const session = await getValidSession();
      if (!session) {
        router.replace('/');
        return;
      }
      setAccessToken(session.accessToken);
    })();
  }, []);

  const handleSubmit = async () => {
    if (!accessToken) return;
    if (!title.trim() || !description.trim()) {
      setError('Title and description are required.');
      return;
    }
    if (workType === 'ON_SITE' && !location.trim()) {
      setError('Location is required for on-site requirements.');
      return;
    }

    setError(null);
    setSubmitting(true);
    try {
      await createRequirement(accessToken, {
        title: title.trim(),
        description: description.trim(),
        skillsNeeded,
        workType,
        experienceRequired: experienceRequired.trim() || undefined,
        salary: salary.trim() || undefined,
        location: location.trim() || undefined,
      });
      router.back();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not post this requirement.');
    } finally {
      setSubmitting(false);
    }
  };

  if (!accessToken) {
    return (
      <SafeAreaView className="flex-1 items-center justify-center" style={{ backgroundColor: AURORA.bg }}>
        <ActivityIndicator color={AURORA.primary} />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView className="flex-1" style={{ backgroundColor: AURORA.bg }}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} className="flex-1">
        <ScrollView contentContainerClassName="px-6 pb-10 pt-6" keyboardShouldPersistTaps="handled">
          <View className="flex-row items-center">
            <Pressable
              onPress={() => router.back()}
              className="h-9 w-9 items-center justify-center rounded-full"
              style={{ backgroundColor: '#fff' }}
              accessibilityRole="button"
              accessibilityLabel="Back"
            >
              <Feather name="arrow-left" size={18} color={AURORA.ink} />
            </Pressable>
            <Text className="ml-3 text-[20px] font-bold tracking-tight" style={{ color: AURORA.ink }}>
              Post a requirement
            </Text>
          </View>

          <Text className="mb-1.5 mt-6 text-[12px] font-bold" style={{ color: AURORA.ink }}>
            Title
          </Text>
          <TextInput
            value={title}
            onChangeText={setTitle}
            placeholder="e.g. Need a plumber this week"
            placeholderTextColor="#97A3AD"
            className="h-12 rounded-[13px] px-3.5 text-[14px] font-medium"
            style={inputStyle}
          />

          <Text className="mb-1.5 mt-4 text-[12px] font-bold" style={{ color: AURORA.ink }}>
            Description
          </Text>
          <TextInput
            value={description}
            onChangeText={setDescription}
            placeholder="What exactly do you need?"
            placeholderTextColor="#97A3AD"
            multiline
            numberOfLines={3}
            className="rounded-[13px] px-3.5 py-3 text-[14px] font-medium"
            style={[inputStyle, { minHeight: 80, textAlignVertical: 'top' }]}
          />

          <View className="mt-4">
            <ChipInput label="Skills needed" placeholder="e.g. Pipe fitting" values={skillsNeeded} onChange={setSkillsNeeded} />
          </View>

          <Text className="mb-1.5 mt-4 text-[12px] font-bold" style={{ color: AURORA.ink }}>
            Work type
          </Text>
          <View className="flex-row" style={{ gap: 8 }}>
            {(['REMOTE', 'ON_SITE'] as const).map((type) => {
              const selected = workType === type;
              return (
                <Pressable
                  key={type}
                  onPress={() => setWorkType(type)}
                  className="flex-1 items-center rounded-[13px] py-3"
                  style={{
                    backgroundColor: selected ? AURORA.avBg : '#fff',
                    borderWidth: selected ? 2 : 1,
                    borderColor: selected ? AURORA.primary : AURORA.line,
                  }}
                >
                  <Text className="text-[13.5px] font-bold" style={{ color: selected ? AURORA.avFg : AURORA.ink2 }}>
                    {type === 'REMOTE' ? 'Remote' : 'On-site'}
                  </Text>
                </Pressable>
              );
            })}
          </View>

          {workType === 'ON_SITE' && (
            <>
              <Text className="mb-1.5 mt-4 text-[12px] font-bold" style={{ color: AURORA.ink }}>
                Location
              </Text>
              <TextInput
                value={location}
                onChangeText={setLocation}
                placeholder="City, area"
                placeholderTextColor="#97A3AD"
                className="h-12 rounded-[13px] px-3.5 text-[14px] font-medium"
                style={inputStyle}
              />
            </>
          )}

          <View className="mt-4 flex-row" style={{ gap: 10 }}>
            <View className="flex-1">
              <Text className="mb-1.5 text-[12px] font-bold" style={{ color: AURORA.ink }}>
                Experience <Text style={{ color: AURORA.ink3, fontWeight: '400' }}>(optional)</Text>
              </Text>
              <TextInput
                value={experienceRequired}
                onChangeText={setExperienceRequired}
                placeholder="e.g. 2+ years"
                placeholderTextColor="#97A3AD"
                className="h-12 rounded-[13px] px-3.5 text-[14px] font-medium"
                style={inputStyle}
              />
            </View>
            <View className="flex-1">
              <Text className="mb-1.5 text-[12px] font-bold" style={{ color: AURORA.ink }}>
                Salary <Text style={{ color: AURORA.ink3, fontWeight: '400' }}>(optional)</Text>
              </Text>
              <TextInput
                value={salary}
                onChangeText={setSalary}
                placeholder="e.g. $50/hr"
                placeholderTextColor="#97A3AD"
                className="h-12 rounded-[13px] px-3.5 text-[14px] font-medium"
                style={inputStyle}
              />
            </View>
          </View>

          <View className="mt-4 rounded-[13px] px-3.5 py-3" style={{ backgroundColor: AURORA.surface2 }}>
            <Text className="text-[11.5px]" style={{ color: AURORA.ink2 }}>
              Visible to your whole circle by default — picking specific subscribers arrives once
              circle building (coming soon) is live.
            </Text>
          </View>

          {error && (
            <Text className="mt-3 text-[11px]" style={{ color: AURORA.danger }}>
              {error}
            </Text>
          )}

          <View className="mt-6">
            <PrimaryButton onPress={handleSubmit} loading={submitting} icon="check">
              Post requirement
            </PrimaryButton>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
