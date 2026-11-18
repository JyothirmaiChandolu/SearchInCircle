import { Pressable, Text, View } from 'react-native';
import Animated, {
  Easing,
  Extrapolation,
  interpolate,
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withTiming,
} from 'react-native-reanimated';
import { Feather } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { useEffect } from 'react';
import { CIRCA } from '../lib/theme';

type Props = {
  icon: keyof typeof Feather.glyphMap;
  tagline: string;
  stepLabel?: string;
  onBack?: () => void;
};

const CYCLE_MS = 5200;

function Dot({ ringStyle }: { ringStyle: ReturnType<typeof useAnimatedStyle> }) {
  return (
    <View style={{ width: 7, height: 7 }}>
      <Animated.View
        pointerEvents="none"
        style={[
          { position: 'absolute', left: -7, top: -7, width: 21, height: 21, borderRadius: 11, backgroundColor: CIRCA.dot },
          ringStyle,
        ]}
      />
      <View style={{ width: 7, height: 7, borderRadius: 4, backgroundColor: CIRCA.dot }} />
    </View>
  );
}

/**
 * Animated gradient hero for the auth flow. A signal relays dot → core → dot every
 * 5.2s round trip, pulsing each stop as it's reached. The core sits as an ordinary
 * flex sibling between two independent track segments, so the moving highlight never
 * geometrically overlaps it (no z-index hack needed).
 *
 * `p` yo-yos 0→1→0→1… continuously (withRepeat reverse:true), so there's no hard
 * reset/teleport at the ends — it genuinely reverses direction at each dot.
 */
export function AuthHero({ icon, tagline, stepLabel = '01 — 03', onBack }: Props) {
  const p = useSharedValue(0);

  useEffect(() => {
    p.value = withRepeat(withTiming(1, { duration: CYCLE_MS / 2, easing: Easing.linear }), -1, true);
  }, [p]);

  const leftSweepStyle = useAnimatedStyle(() => {
    const pct = interpolate(p.value, [0, 0.5], [0, 88], Extrapolation.CLAMP);
    const opacity = interpolate(p.value, [0, 0.46, 0.5], [1, 1, 0], Extrapolation.CLAMP);
    return { left: `${pct}%`, opacity };
  });

  const rightSweepStyle = useAnimatedStyle(() => {
    const pct = interpolate(p.value, [0.5, 1], [0, 88], Extrapolation.CLAMP);
    const opacity = interpolate(p.value, [0.5, 0.54, 1], [0, 1, 1], Extrapolation.CLAMP);
    return { left: `${pct}%`, opacity };
  });

  const coreRingStyle = useAnimatedStyle(() => {
    const o = interpolate(p.value, [0.44, 0.5, 0.56], [0, 1, 0], Extrapolation.CLAMP);
    return { opacity: o, transform: [{ scale: 1 + o * 0.22 }] };
  });

  const dotLeftRingStyle = useAnimatedStyle(() => {
    const o = interpolate(p.value, [0, 0.06], [1, 0], Extrapolation.CLAMP);
    return { opacity: o * 0.8, transform: [{ scale: 1 + o * 1.4 }] };
  });

  const dotRightRingStyle = useAnimatedStyle(() => {
    const o = interpolate(p.value, [0.94, 1], [0, 1], Extrapolation.CLAMP);
    return { opacity: o * 0.8, transform: [{ scale: 1 + o * 1.4 }] };
  });

  return (
    <View style={{ height: 290, overflow: 'hidden' }}>
      <LinearGradient
        colors={CIRCA.heroGradient}
        start={{ x: 0, y: 0 }}
        end={{ x: 0.85, y: 1 }}
        style={{ flex: 1, paddingHorizontal: 24, paddingTop: 22, paddingBottom: 20 }}
      >
        <View
          pointerEvents="none"
          style={{
            position: 'absolute',
            width: 220,
            height: 220,
            right: -100,
            bottom: -120,
            borderRadius: 110,
            backgroundColor: CIRCA.heroBlur,
          }}
        />

        <View className="flex-row items-center">
          {onBack ? (
            <Pressable
              onPress={onBack}
              accessibilityRole="button"
              accessibilityLabel="Back"
              className="h-8 w-8 items-center justify-center rounded-full"
              style={{ backgroundColor: 'rgba(255,255,255,0.14)' }}
            >
              <Feather name="arrow-left" size={16} color="#fff" />
            </Pressable>
          ) : (
            <View className="h-[35px] w-[35px] items-center justify-center rounded-[10px]" style={{ backgroundColor: '#fff' }}>
              <Feather name="link" size={18} color={CIRCA.brand} />
            </View>
          )}
          <Text
            className="ml-2.5 text-[12px] font-bold uppercase tracking-[0.2em]"
            style={{ color: '#fff', fontFamily: 'Manrope_800ExtraBold' }}
          >
            CIRCA
          </Text>
        </View>

        <View className="flex-1 justify-center">
          <View className="flex-row justify-between">
            <Text className="text-[8px] font-bold uppercase tracking-[0.12em]" style={{ color: 'rgba(255,255,255,0.47)' }}>
              TRUSTED NETWORK
            </Text>
            <Text className="text-[8px] font-bold uppercase tracking-[0.12em]" style={{ color: 'rgba(255,255,255,0.47)' }}>
              PRIVATE BY DESIGN
            </Text>
          </View>

          <View className="my-4 flex-row items-center">
            <Dot ringStyle={dotLeftRingStyle} />

            <View style={{ flex: 1, height: 10, marginHorizontal: 2, justifyContent: 'center' }}>
              <View style={{ height: 1, backgroundColor: 'rgba(255,255,255,0.13)' }} />
              <Animated.View
                pointerEvents="none"
                style={[
                  { position: 'absolute', top: 4, width: 22, height: 2, borderRadius: 1, backgroundColor: '#DDD6FE' },
                  leftSweepStyle,
                ]}
              />
            </View>

            <View
              className="h-16 w-16 items-center justify-center rounded-[18px]"
              style={{ marginHorizontal: 10, borderWidth: 1, borderColor: 'rgba(255,255,255,0.36)', backgroundColor: 'rgba(255,255,255,0.12)' }}
            >
              <Animated.View
                pointerEvents="none"
                style={[{ position: 'absolute', width: 64, height: 64, borderRadius: 18, borderWidth: 1, borderColor: CIRCA.dot }, coreRingStyle]}
              />
              <Feather name={icon} size={26} color="#fff" />
            </View>

            <View style={{ flex: 1, height: 10, marginHorizontal: 2, justifyContent: 'center' }}>
              <View style={{ height: 1, backgroundColor: 'rgba(255,255,255,0.13)' }} />
              <Animated.View
                pointerEvents="none"
                style={[
                  { position: 'absolute', top: 4, width: 22, height: 2, borderRadius: 1, backgroundColor: '#DDD6FE' },
                  rightSweepStyle,
                ]}
              />
            </View>

            <Dot ringStyle={dotRightRingStyle} />
          </View>

          <Text
            numberOfLines={1}
            adjustsFontSizeToFit
            minimumFontScale={0.75}
            className="text-[18px] leading-[24px] tracking-tight"
            style={{ color: '#fff', fontFamily: 'Manrope_700Bold' }}
          >
            {tagline}
          </Text>
        </View>

        <Text className="self-end text-[8px] font-bold uppercase tracking-[0.13em]" style={{ color: 'rgba(255,255,255,0.42)' }}>
          {stepLabel}
        </Text>
      </LinearGradient>
    </View>
  );
}
