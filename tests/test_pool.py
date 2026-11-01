import unittest
from src.pool import AddressPool, PoolManager

class TestAddressPool(unittest.TestCase):
    def setUp(self):

        self.pool = AddressPool(
            name="HQ_DATA",
            cidr="192.0.2.0/29",
            vlan_id=10,
            gateway="192.0.2.1",
            reserved_ips=["192.0.2.2"]
        )

    def test_allocation_lifecycle(self):
        ip1 = self.pool.allocate_next("host-a", "Workstation A", "2026-10-31T05:00:00")
        self.assertEqual(ip1, "192.0.2.3")

        ip2 = self.pool.allocate_next("host-b", "Workstation B", "2026-10-31T05:01:00")
        self.assertEqual(ip2, "192.0.2.4")


        with self.assertRaises(ValueError):
            self.pool.allocate_next("host-a", "Duplicate Name", "2026-10-31T05:02:00")


        released = self.pool.release("host-a")
        self.assertEqual(released, "192.0.2.3")
        self.assertNotIn("192.0.2.3", self.pool.allocations)

    def test_pool_exhaustion(self):
        self.pool.allocate_next("h1", "", "")
        self.pool.allocate_next("h2", "", "")
        self.pool.allocate_next("h3", "", "")
        self.pool.allocate_next("h4", "", "")
        with self.assertRaises(RuntimeError):
            self.pool.allocate_next("h5", "", "")

    def test_pool_overlap_prevention(self):
        mgr = PoolManager()
        mgr.add_pool(self.pool)
        dup = AddressPool(name="CONFLICT", cidr="192.0.2.0/28", vlan_id=20, gateway="192.0.2.14")
        with self.assertRaises(ValueError):
            mgr.add_pool(dup)

if __name__ == "__main__":
    unittest.main()
