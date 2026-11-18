import { ActivityIndicator, Pressable, Text } from 'react-native';
import Animated, { useAnimatedStyle, useSharedValue, withSpring } from 'react-native-reanimated';
import { Feather } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { CIRCA } from '../lib/theme';

type Props = {
  children: string;
  onPress: () => void;
  icon?: keyof typeof Feather.glyphMap;
  loading?: boolean;
  disabled?: boolean;
};

/** Gradient CTA with a subtle press-scale (CIRCA button style). */
export function PrimaryButton({ children, onPress, icon = 'arrow-right', loading, disabled }: Props) {
  const scale = useSharedValue(1);
  const animatedStyle = useAnimatedStyle(() => ({ transform: [{ scale: scale.value }] }));
  const isDisabled = disabled || loading;

  return (
    <Animated.View style={animatedStyle}>
      <Pressable
        onPress={onPress}
        // eslint-disable-next-line react-hooks/immutability -- Reanimated SharedValue mutation is the documented API
        onPressIn={() => (scale.value = withSpring(0.97, { damping: 16, stiffness: 300 }))}
        // eslint-disable-next-line react-hooks/immutability -- Reanimated SharedValue mutation is the documented API
        onPressOut={() => (scale.value = withSpring(1, { damping: 16, stiffness: 300 }))}
        disabled={isDisabled}
        accessibilityRole="button"
        accessibilityLabel={children}
        style={{
          opacity: isDisabled ? 0.6 : 1,
          borderRadius: 15,
          shadowColor: CIRCA.brandDark,
          shadowOpacity: 0.3,
          shadowRadius: 16,
          shadowOffset: { width: 0, height: 10 },
          elevation: 6,
        }}
      >
        <LinearGradient
          colors={CIRCA.buttonGradient}
          locations={[0, 0.62, 1]}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1.1 }}
          style={{
            minHeight: 54,
            flexDirection: 'row',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 10,
            borderRadius: 15,
            overflow: 'hidden',
          }}
        >
          {loading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <>
              <Text className="text-[15px] font-bold text-white" style={{ fontFamily: 'DMSans_700Bold' }}>
                {children}
              </Text>
              <Feather name={icon} size={18} color="#fff" />
            </>
          )}
        </LinearGradient>
      </Pressable>
    </Animated.View>
  );
}
