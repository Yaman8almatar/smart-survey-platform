import 'package:flutter/material.dart';

/// The topic icon shown on an unselected interest chip.
IconData interestIcon(String code) => switch (code) {
  'TECHNOLOGY' => Icons.devices_outlined,
  'EDUCATION' => Icons.school_outlined,
  'HEALTH' => Icons.favorite_border,
  'SPORTS' => Icons.sports_soccer_outlined,
  'FOOD' => Icons.restaurant_outlined,
  'TRAVEL' => Icons.flight_outlined,
  'SHOPPING' => Icons.shopping_bag_outlined,
  'FINANCE' => Icons.payments_outlined,
  'CAREERS' => Icons.work_outline,
  'ARTS' => Icons.palette_outlined,
  'ENTERTAINMENT' => Icons.movie_outlined,
  'ENVIRONMENT' => Icons.eco_outlined,
  _ => Icons.label_outline,
};
