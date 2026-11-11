import { Stack, useLocalSearchParams, useRouter } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { type Pc, getClub, listPcs, listZones } from '@/api/endpoints';
import { formatKzt, openingHoursLabel, t } from '@/i18n';
import { useLoad } from '@/lib/useLoad';
import { Card, Chip, Loadable, Screen } from '@/ui/components';
import { font, space } from '@/ui/theme';

/** `RTX 4060 · 240 Hz` from the free-form specs object. */
function specsLine(specs: Pc['specs']): string {
  return Object.values(specs)
    .filter((value) => typeof value === 'string' || typeof value === 'number')
    .join(' · ');
}

/** One club: its zones as a filter and its PCs. */
export default function ClubScreen() {
  const { clubId } = useLocalSearchParams<{ clubId: string }>();
  const router = useRouter();
  const [zoneId, setZoneId] = useState<string | null>(null);

  const state = useLoad(async () => {
    const [club, zones, pcs] = await Promise.all([
      getClub(clubId),
      listZones(clubId),
      listPcs(clubId),
    ]);
    return { club, zones, pcs };
  }, `club:${clubId}`);

  return (
    <Screen>
      <Stack.Screen options={{ title: state.data?.club.name ?? '' }} />
      <Loadable state={state}>
        {({ club, zones, pcs }) => {
          const visible = zoneId === null ? pcs : pcs.filter((pc) => pc.zone_id === zoneId);
          return (
            <>
              <Text style={font.small}>
                {club.city}, {club.address} · {openingHoursLabel(club)}
              </Text>
              <View style={styles.chips}>
                <Chip
                  label={t.club.allZones}
                  selected={zoneId === null}
                  onPress={() => setZoneId(null)}
                />
                {zones.map((zone) => (
                  <Chip
                    key={zone.id}
                    label={zone.name}
                    sublabel={`${formatKzt(zone.price_per_hour_kzt)} ${t.common.perHour}`}
                    selected={zoneId === zone.id}
                    onPress={() => setZoneId(zone.id)}
                  />
                ))}
              </View>
              {visible.length === 0 ? <Text style={font.small}>{t.club.empty}</Text> : null}
              {visible.map((pc) => (
                <Card
                  key={pc.id}
                  onPress={() =>
                    router.push({
                      pathname: '/pcs/[pcId]',
                      params: { pcId: pc.id, clubId: club.id },
                    })
                  }
                >
                  <View style={styles.pcHeader}>
                    <Text style={font.heading}>{pc.label}</Text>
                    <Text style={font.body}>
                      {formatKzt(pc.price_per_hour_kzt)} {t.common.perHour}
                    </Text>
                  </View>
                  <Text style={font.small}>
                    {[pc.zone_name, specsLine(pc.specs)].filter(Boolean).join(' · ')}
                  </Text>
                </Card>
              ))}
            </>
          );
        }}
      </Loadable>
    </Screen>
  );
}

const styles = StyleSheet.create({
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: space.sm },
  pcHeader: { flexDirection: 'row', justifyContent: 'space-between', gap: space.md },
});
